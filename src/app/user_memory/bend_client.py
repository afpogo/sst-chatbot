from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from app.service_auth import ClientCredentialTokenProvider
from app.user_memory.contracts import MemoryProposalCandidate
from app.user_memory.contracts import MemoryProposalReceipt
from app.user_memory.contracts import UserMemoryPortError


class BendUserMemoryClient:
    """Single-attempt M2M adapter with one exact grant per operation."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token_provider=None,
        timeout: float = 5.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("SST_API_URL", "http://sst:4000")).rstrip("/")
        self.token_provider = token_provider or ClientCredentialTokenProvider.chatbot_from_env()
        self.timeout = timeout

    def recall_candidates(
        self,
        *,
        conversation_ref: str,
        correlation_id: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        result = self._post(
            "/4uentes/v1/internal/user-memory/recall-candidates",
            "user-memory:recall",
            {
                "conversationRef": conversation_ref,
                "correlationId": correlation_id,
                "filters": {},
                "limit": limit,
            },
        )
        if not isinstance(result.get("scope"), dict) or not isinstance(result.get("records"), list):
            raise UserMemoryPortError("Bend returned invalid recall candidates")
        return result

    def audit_recall(
        self,
        *,
        conversation_ref: str,
        correlation_id: str,
        retrieved_memory_ids: list[str],
        citation_refs: list[dict[str, str]],
    ) -> dict[str, Any]:
        return self._post(
            "/4uentes/v1/internal/user-memory/recalls",
            "user-memory:recall",
            {
                "conversationRef": conversation_ref,
                "correlationId": correlation_id,
                "retrievedMemoryIds": retrieved_memory_ids,
                "citationRefs": citation_refs,
                "filters": {"status": "active"},
            },
        )

    def propose(
        self,
        *,
        conversation_ref: str,
        correlation_id: str,
        idempotency_key: str,
        candidate: MemoryProposalCandidate,
    ) -> MemoryProposalReceipt:
        result = self._post(
            "/4uentes/v1/internal/user-memory/proposals",
            "user-memory:propose",
            {
                "conversationRef": conversation_ref,
                "correlationId": correlation_id,
                "idempotencyKey": idempotency_key,
                "candidate": candidate.bend_payload(),
            },
        )
        try:
            return MemoryProposalReceipt.model_validate(result)
        except ValueError as exc:
            raise UserMemoryPortError("Bend returned an invalid memory proposal receipt") from exc

    def _post(self, path: str, scope: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            token = self.token_provider.get_token("sst-api", scope)
            request = urllib.request.Request(
                f"{self.base_url}{path}",
                data=json.dumps(body).encode(),
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            raise UserMemoryPortError(f"Bend memory request failed with HTTP {exc.code}") from exc
        except Exception as exc:
            raise UserMemoryPortError("Bend memory transport failed") from exc
        if not isinstance(result, dict):
            raise UserMemoryPortError("Bend returned an invalid memory response")
        return result
