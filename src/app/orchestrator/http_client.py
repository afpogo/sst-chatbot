from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from app.orchestrator.port import OrchestratorPortError
from app.orchestrator.types import HandoffPayload
from app.orchestrator.types import HandoffReceipt
from app.orchestrator.types import ReviewEvidence
from app.service_auth import ClientCredentialTokenProvider


class HttpOrchestratorClient:
    """Durable handoff adapter. Each submit performs exactly one HTTP attempt."""

    def __init__(self, *, base_url: str | None = None, token_provider=None, timeout: float = 5.0) -> None:
        self.base_url = (base_url or os.getenv("SST_API_URL", "http://sst:4000")).rstrip("/")
        self.token_provider = token_provider or ClientCredentialTokenProvider.chatbot_from_env()
        self.timeout = timeout

    def submit(self, payload: HandoffPayload, *, review_evidence: ReviewEvidence | None = None) -> HandoffReceipt:
        body = payload.model_dump(mode="json")
        if review_evidence is not None:
            body["review_evidence"] = review_evidence.model_dump(mode="json")
        try:
            token = self.token_provider.get_token("sst-api", "agent-handoff:submit")
            request = urllib.request.Request(
                f"{self.base_url}/4uentes/v1/agent-handoffs",
                data=json.dumps(body).encode(),
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                receipt = json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                receipt = json.loads(exc.read())
            except (ValueError, json.JSONDecodeError):
                receipt = None
            if exc.code in (400, 409, 422) and isinstance(receipt, dict):
                try:
                    return HandoffReceipt.model_validate(receipt)
                except ValueError as validation_error:
                    raise OrchestratorPortError("orchestrator returned an invalid receipt") from validation_error
            raise OrchestratorPortError(f"orchestrator handoff failed with HTTP {exc.code}") from exc
        except Exception as exc:
            raise OrchestratorPortError("orchestrator handoff transport failed") from exc
        try:
            return HandoffReceipt.model_validate(receipt)
        except ValueError as exc:
            raise OrchestratorPortError("orchestrator returned an invalid receipt") from exc
