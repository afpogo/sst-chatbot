from __future__ import annotations

from pydantic import BaseModel

from app.agents.lifecycle import AgentLifecycle
from app.agents.lifecycle import advance_lifecycle
from app.agents.lifecycle import record_external_receipt
from app.memory.handoff import to_handoff_payload
from app.memory.types import OperationalRecord
from app.memory.validation import validate_record
from app.orchestrator.port import OrchestratorPort
from app.orchestrator.port import OrchestratorPortError
from app.orchestrator.store import payload_fingerprint
from app.orchestrator.types import HandoffDecision
from app.orchestrator.types import HandoffIssue
from app.orchestrator.types import HandoffPayload
from app.orchestrator.types import HandoffReceipt
from app.orchestrator.types import ReviewEvidence
from app.orchestrator.validation import validate_handoff_payload


class HandoffCoordinationResult(BaseModel):
    lifecycle: AgentLifecycle
    local_decision: HandoffDecision
    receipt: HandoffReceipt | None = None
    error_code: str = ""


class IntentHandoffCoordinator:
    def __init__(self, port: OrchestratorPort) -> None:
        self.port = port

    def submit(
        self,
        intent: OperationalRecord,
        lifecycle: AgentLifecycle,
        *,
        review_evidence: ReviewEvidence | None = None,
        actor: str,
        reason: str,
        evidence_ref: str = "",
    ) -> HandoffCoordinationResult:
        self._require_matching_context(intent, lifecycle)
        if lifecycle.state != "planned":
            raise ValueError("handoff coordination requires lifecycle state planned")

        record_validation = validate_record(intent)
        if not record_validation.accepted:
            local_decision = HandoffDecision(
                accepted=False,
                status="rejected_by_policy",
                issues=tuple(
                    HandoffIssue(
                        code=issue.code,
                        message=issue.message,
                        severity=issue.severity,
                    )
                    for issue in record_validation.issues
                ),
            )
            rejected = advance_lifecycle(
                lifecycle,
                "rejected",
                actor=actor,
                reason="local intent validation rejected the record",
                input_ref=intent.id,
                output_ref=evidence_ref,
                external_correlation_id=intent.correlation_id,
            )
            return HandoffCoordinationResult(
                lifecycle=rejected,
                local_decision=local_decision,
                error_code=local_decision.issues[0].code,
            )

        payload = HandoffPayload(**to_handoff_payload(intent))
        local_decision = validate_handoff_payload(
            payload,
            human_reviewed=review_evidence is not None,
        )
        if not local_decision.accepted:
            rejected = advance_lifecycle(
                lifecycle,
                "rejected",
                actor=actor,
                reason="local handoff validation rejected the intent",
                input_ref=intent.id,
                output_ref=evidence_ref,
                external_correlation_id=intent.correlation_id,
            )
            return HandoffCoordinationResult(
                lifecycle=rejected,
                local_decision=local_decision,
                error_code=local_decision.issues[0].code,
            )

        effective_evidence_ref = (
            review_evidence.evidence_ref if review_evidence else evidence_ref
        )
        validated = advance_lifecycle(
            lifecycle,
            "validated_for_handoff",
            actor=actor,
            reason=reason,
            input_ref=intent.id,
            output_ref=effective_evidence_ref,
            external_correlation_id=intent.correlation_id,
        )
        requested = advance_lifecycle(
            validated,
            "handoff_requested",
            actor=actor,
            reason="submitted through the configured orchestrator port",
            input_ref=intent.id,
            output_ref=effective_evidence_ref,
            external_correlation_id=intent.correlation_id,
        )

        try:
            receipt = self.port.submit(
                payload,
                review_evidence=review_evidence,
            )
        except OrchestratorPortError:
            failed = advance_lifecycle(
                requested,
                "failed",
                actor=actor,
                reason="orchestrator port failed",
                input_ref=intent.id,
                output_ref=evidence_ref,
                external_correlation_id=intent.correlation_id,
            )
            return HandoffCoordinationResult(
                lifecycle=failed,
                local_decision=local_decision,
                error_code="orchestrator_port_error",
            )

        receipt_mismatch = self._receipt_mismatch(
            payload,
            receipt,
            review_evidence=review_evidence,
        )
        if receipt_mismatch:
            failed = advance_lifecycle(
                requested,
                "failed",
                actor=actor,
                reason="orchestrator port returned a receipt for different context",
                input_ref=intent.id,
                output_ref=receipt.receipt_id,
                external_correlation_id=intent.correlation_id,
            )
            return HandoffCoordinationResult(
                lifecycle=failed,
                local_decision=local_decision,
                receipt=receipt,
                error_code="receipt_context_mismatch",
            )

        observed = record_external_receipt(
            requested,
            receipt_id=receipt.receipt_id,
            status=receipt.status,
            correlation_id=receipt.correlation_id,
        )
        if receipt.status in {"rejected_by_policy", "conflict"}:
            rejected = advance_lifecycle(
                observed,
                "rejected",
                actor=actor,
                reason=f"orchestrator port returned {receipt.status}",
                input_ref=intent.id,
                output_ref=receipt.receipt_id,
                external_correlation_id=receipt.correlation_id,
            )
            return HandoffCoordinationResult(
                lifecycle=rejected,
                local_decision=local_decision,
                receipt=receipt,
                error_code=receipt.status,
            )

        return HandoffCoordinationResult(
            lifecycle=observed,
            local_decision=local_decision,
            receipt=receipt,
        )

    @staticmethod
    def _require_matching_context(
        intent: OperationalRecord,
        lifecycle: AgentLifecycle,
    ) -> None:
        if intent.record_type != "intent":
            raise ValueError("handoff coordination requires an intent record")
        if lifecycle.operation_intent_id != intent.id:
            raise ValueError("lifecycle operation_intent_id does not match intent")
        if lifecycle.correlation_id != intent.correlation_id:
            raise ValueError("lifecycle correlation_id does not match intent")

    @staticmethod
    def _receipt_mismatch(
        payload: HandoffPayload,
        receipt: HandoffReceipt,
        *,
        review_evidence: ReviewEvidence | None,
    ) -> bool:
        return any(
            (
                receipt.operation_intent_id != payload.operation_intent_id,
                receipt.capability_id != payload.capability_id,
                receipt.tenant_id != payload.tenant_id,
                receipt.user_id != payload.user_id,
                receipt.idempotency_key != payload.idempotency_key,
                receipt.correlation_id != payload.correlation_id,
                receipt.audit_metadata != payload.audit_metadata,
                receipt.payload_fingerprint != payload_fingerprint(payload),
                receipt.review_evidence != review_evidence,
            )
        )
