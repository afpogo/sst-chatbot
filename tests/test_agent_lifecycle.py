from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.agents import AgentLifecycle
from app.agents import ExternalOwnershipAcceptance
from app.agents import accept_external_handoff_ownership
from app.agents import advance_lifecycle
from app.agents import record_external_receipt


def advance_to_planned() -> AgentLifecycle:
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


def test_lifecycle_is_append_only_and_preserves_transition_audit() -> None:
    original = AgentLifecycle(operation_intent_id="intent-1", correlation_id="corr-1")

    classified = advance_lifecycle(
        original,
        "classified",
        actor="planner",
        reason="known capability",
        input_ref="request-1",
        output_ref="plan-1",
        external_correlation_id="corr-1",
    )

    assert original.state == "requested"
    assert original.history == ()
    assert classified.state == "classified"
    assert classified.history[0].actor == "planner"
    assert classified.history[0].input_ref == "request-1"
    assert classified.history[0].output_ref == "plan-1"


def test_invalid_jump_reverse_and_terminal_exit_are_rejected() -> None:
    lifecycle = AgentLifecycle(operation_intent_id="intent-1", correlation_id="corr-1")
    with pytest.raises(ValueError, match="requested -> planned"):
        advance_lifecycle(lifecycle, "planned", actor="test", reason="invalid")

    planned = advance_to_planned()
    with pytest.raises(ValueError, match="planned -> classified"):
        advance_lifecycle(planned, "classified", actor="test", reason="reverse")

    rejected = advance_lifecycle(
        planned,
        "rejected",
        actor="test",
        reason="policy",
    )
    with pytest.raises(ValueError, match="rejected -> requested"):
        advance_lifecycle(rejected, "requested", actor="test", reason="restart")


def test_lifecycle_cannot_be_forged_with_state_without_history() -> None:
    with pytest.raises(ValidationError, match="does not match transition history"):
        AgentLifecycle(
            operation_intent_id="intent-1",
            correlation_id="corr-1",
            state="planned",
        )


def test_handoff_ownership_requires_typed_external_acceptance() -> None:
    lifecycle = advance_to_planned()
    lifecycle = advance_lifecycle(
        lifecycle,
        "validated_for_handoff",
        actor="test",
        reason="validated",
    )
    lifecycle = advance_lifecycle(
        lifecycle,
        "handoff_requested",
        actor="test",
        reason="submitted",
    )

    with pytest.raises(ValueError, match="requires accept_external"):
        advance_lifecycle(
            lifecycle,
            "handoff_accepted",
            actor="fake",
            reason="not enough",
        )

    acceptance = ExternalOwnershipAcceptance(
        receipt_id="real-receipt-1",
        correlation_id="corr-1",
        accepted_by="4uentes-orchestor",
        evidence_ref="external-receipt-1",
    )

    with pytest.raises(ValueError, match="receipt was not observed"):
        accept_external_handoff_ownership(lifecycle, acceptance)

    fake_observed = record_external_receipt(
        lifecycle,
        receipt_id="fake-receipt-1",
        status="accepted_for_review",
        correlation_id="corr-1",
    )
    fake_acceptance = acceptance.model_copy(update={"receipt_id": "fake-receipt-1"})
    with pytest.raises(ValueError, match="does not accept execution ownership"):
        accept_external_handoff_ownership(fake_observed, fake_acceptance)

    real_observed = record_external_receipt(
        lifecycle,
        receipt_id="real-receipt-1",
        status="execution_ownership_accepted",
        correlation_id="corr-1",
    )
    accepted = accept_external_handoff_ownership(real_observed, acceptance)
    assert accepted.state == "handoff_accepted"
    assert accepted.history[-1].input_ref == "real-receipt-1"
