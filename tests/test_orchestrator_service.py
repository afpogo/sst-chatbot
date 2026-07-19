from __future__ import annotations

from app.agents import AgentLifecycle
from app.agents import advance_lifecycle
from app.memory import AuditMetadata
from app.memory import OperationalRecord
from app.memory import stable_body_hash
from app.orchestrator import FakeOrchestratorClient
from app.orchestrator import IntentHandoffCoordinator
from app.orchestrator import ReviewEvidence


def make_intent(operation: str = "workspace.generate_bundle") -> OperationalRecord:
    body = {"summary": operation}
    return OperationalRecord(
        id="intent-1",
        record_type="intent",
        tenant_id="tenant-1",
        user_id="user-1",
        correlation_id="corr-1",
        idempotency_key="idem-1",
        producer="test",
        capability_id="capability.inbound.sst-chatbot-agent-handoff",
        tags=("domain:sst", "kind:intent"),
        provenance={"was_attributed_to": "pytest"},
        body=body,
        body_hash=stable_body_hash(body),
        audit_metadata=AuditMetadata(
            origin_service="sst-chatbot",
            created_by="pytest",
            reason="unit test",
        ),
        payload={
            "requested_operation": operation,
            "priority": "normal",
            "requested_retry_policy": "none",
        },
    )


def planned_lifecycle() -> AgentLifecycle:
    lifecycle = AgentLifecycle(operation_intent_id="intent-1", correlation_id="corr-1")
    lifecycle = advance_lifecycle(
        lifecycle,
        "classified",
        actor="test",
        reason="classified",
    )
    return advance_lifecycle(
        lifecycle,
        "planned",
        actor="test",
        reason="planned",
    )


def test_safe_intent_reaches_fake_review_without_claiming_execution_ownership() -> None:
    result = IntentHandoffCoordinator(FakeOrchestratorClient()).submit(
        make_intent(),
        planned_lifecycle(),
        actor="test",
        reason="validated local proposal",
        evidence_ref="local-test",
    )

    assert result.receipt is not None
    assert result.receipt.status == "accepted_for_review"
    assert result.lifecycle.state == "handoff_requested"
    assert result.lifecycle.external_receipts[0].receipt_id == result.receipt.receipt_id
    assert [item.to_state for item in result.lifecycle.history[-2:]] == [
        "validated_for_handoff",
        "handoff_requested",
    ]


def test_review_operation_is_rejected_locally_without_review() -> None:
    result = IntentHandoffCoordinator(FakeOrchestratorClient()).submit(
        make_intent("workspace.apply_patch"),
        planned_lifecycle(),
        actor="test",
        reason="review check",
    )

    assert result.receipt is None
    assert result.lifecycle.state == "rejected"
    assert result.error_code == "human_review_required"


def test_review_operation_can_reach_fake_after_explicit_review() -> None:
    result = IntentHandoffCoordinator(FakeOrchestratorClient()).submit(
        make_intent("workspace.apply_patch"),
        planned_lifecycle(),
        review_evidence=ReviewEvidence(
            reviewer="reviewer",
            reason="approved patch proposal",
            evidence_ref="review-1",
        ),
        actor="reviewer",
        reason="review evidence recorded",
        evidence_ref="review-1",
    )

    assert result.receipt is not None
    assert result.receipt.status == "accepted_for_review"
    assert result.lifecycle.state == "handoff_requested"


def test_unknown_operation_is_rejected_before_calling_the_port() -> None:
    class RecordingPort:
        called = False

        def submit(self, payload, *, review_evidence=None):
            self.called = True
            raise AssertionError("port must not be called")

    port = RecordingPort()
    result = IntentHandoffCoordinator(port).submit(
        make_intent("totally.unknown"),
        planned_lifecycle(),
        actor="test",
        reason="policy check",
    )

    assert port.called is False
    assert result.lifecycle.state == "rejected"
    assert result.error_code == "unsupported_operation"


def test_foreign_receipt_fails_without_binding_it_to_the_lifecycle() -> None:
    class ForeignReceiptPort:
        def submit(self, payload, *, review_evidence=None):
            valid = FakeOrchestratorClient().submit(payload)
            return valid.model_copy(update={"tenant_id": "another-tenant"})

    result = IntentHandoffCoordinator(ForeignReceiptPort()).submit(
        make_intent(),
        planned_lifecycle(),
        actor="test",
        reason="binding check",
    )

    assert result.lifecycle.state == "failed"
    assert result.lifecycle.external_receipts == ()
    assert result.error_code == "receipt_context_mismatch"


def test_review_evidence_crosses_the_port_and_is_returned_in_receipt() -> None:
    review = ReviewEvidence(
        reviewer="reviewer",
        reason="approved patch proposal",
        evidence_ref="review-2",
    )
    result = IntentHandoffCoordinator(FakeOrchestratorClient()).submit(
        make_intent("workspace.apply_patch"),
        planned_lifecycle(),
        review_evidence=review,
        actor="reviewer",
        reason="reviewed",
    )

    assert result.receipt is not None
    assert result.receipt.review_evidence == review


def test_receipt_with_wrong_payload_fingerprint_fails_binding() -> None:
    class WrongFingerprintPort:
        def submit(self, payload, *, review_evidence=None):
            valid = FakeOrchestratorClient().submit(payload)
            return valid.model_copy(update={"payload_fingerprint": "wrong"})

    result = IntentHandoffCoordinator(WrongFingerprintPort()).submit(
        make_intent(),
        planned_lifecycle(),
        actor="test",
        reason="fingerprint check",
    )

    assert result.lifecycle.state == "failed"
    assert result.error_code == "receipt_context_mismatch"
