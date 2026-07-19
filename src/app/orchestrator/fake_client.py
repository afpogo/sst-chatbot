from __future__ import annotations

from app.orchestrator.store import HandoffStore
from app.orchestrator.store import InMemoryHandoffStore
from app.orchestrator.store import payload_fingerprint
from app.orchestrator.types import HandoffDecision
from app.orchestrator.types import HandoffIssue
from app.orchestrator.types import HandoffPayload
from app.orchestrator.types import HandoffReceipt
from app.orchestrator.types import ReviewEvidence
from app.orchestrator.validation import validate_handoff_payload


class FakeOrchestratorClient:
    def __init__(self, store: HandoffStore | None = None) -> None:
        self.store = store or InMemoryHandoffStore()

    def submit(
        self,
        payload: HandoffPayload | dict[str, object],
        *,
        review_evidence: ReviewEvidence | None = None,
    ) -> HandoffReceipt:
        resolved_payload = (
            payload if isinstance(payload, HandoffPayload) else HandoffPayload(**payload)
        )
        fingerprint = payload_fingerprint(resolved_payload)
        existing = self.store.find_by_idempotency(resolved_payload.idempotency_key)

        if existing:
            if existing.payload_fingerprint == fingerprint:
                return existing.model_copy(
                    update={
                        "status": "duplicate",
                        "decision": HandoffDecision(
                            accepted=True,
                            status="duplicate",
                        ),
                    }
                )
            return _receipt(
                resolved_payload,
                fingerprint,
                HandoffDecision(
                    accepted=False,
                    status="conflict",
                    issues=(
                        HandoffIssue(
                            code="idempotency_conflict",
                            message="idempotency_key already exists with a different payload",
                        ),
                    ),
                ),
                review_evidence=review_evidence,
            )

        decision = validate_handoff_payload(
            resolved_payload,
            human_reviewed=review_evidence is not None,
        )
        receipt = _receipt(
            resolved_payload,
            fingerprint,
            decision,
            review_evidence=review_evidence,
        )
        if decision.accepted:
            self.store.append(receipt)
        return receipt


def _receipt(
    payload: HandoffPayload,
    fingerprint: str,
    decision: HandoffDecision,
    review_evidence: ReviewEvidence | None = None,
) -> HandoffReceipt:
    return HandoffReceipt(
        receipt_id=f"fake-orchestrator-receipt-{payload.idempotency_key}",
        status=decision.status,
        operation_intent_id=payload.operation_intent_id,
        capability_id=payload.capability_id,
        tenant_id=payload.tenant_id,
        user_id=payload.user_id,
        idempotency_key=payload.idempotency_key,
        correlation_id=payload.correlation_id,
        audit_metadata=payload.audit_metadata,
        review_evidence=review_evidence,
        decision=decision,
        payload_fingerprint=fingerprint,
    )
