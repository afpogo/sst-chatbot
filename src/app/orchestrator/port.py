from __future__ import annotations

from typing import Protocol

from app.orchestrator.types import HandoffPayload
from app.orchestrator.types import HandoffReceipt
from app.orchestrator.types import ReviewEvidence


class OrchestratorPortError(RuntimeError):
    """Normalized transport error for replaceable orchestrator adapters."""


class OrchestratorPort(Protocol):
    def submit(
        self,
        payload: HandoffPayload,
        *,
        review_evidence: ReviewEvidence | None = None,
    ) -> HandoffReceipt:
        ...
