from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator


AgentLifecycleState = Literal[
    "requested",
    "classified",
    "planned",
    "validated_for_handoff",
    "handoff_requested",
    "handoff_accepted",
    "completed",
    "failed",
    "rejected",
]

ALLOWED_LIFECYCLE_TRANSITIONS: dict[
    AgentLifecycleState,
    frozenset[AgentLifecycleState],
] = {
    "requested": frozenset({"classified", "rejected", "failed"}),
    "classified": frozenset({"planned", "rejected", "failed"}),
    "planned": frozenset({"validated_for_handoff", "rejected", "failed"}),
    "validated_for_handoff": frozenset(
        {"handoff_requested", "rejected", "failed"}
    ),
    "handoff_requested": frozenset({"handoff_accepted", "rejected", "failed"}),
    "handoff_accepted": frozenset({"completed", "failed"}),
    "completed": frozenset(),
    "failed": frozenset(),
    "rejected": frozenset(),
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


class LifecycleTransition(BaseModel):
    model_config = ConfigDict(frozen=True)

    from_state: AgentLifecycleState
    to_state: AgentLifecycleState
    actor: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    occurred_at: datetime = Field(default_factory=_utc_now)
    input_ref: str = ""
    output_ref: str = ""
    external_correlation_id: str = ""


class ExternalReceiptObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    receipt_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    observed_at: datetime = Field(default_factory=_utc_now)


class ExternalOwnershipAcceptance(BaseModel):
    model_config = ConfigDict(frozen=True)

    receipt_id: str = Field(min_length=1)
    status: Literal["execution_ownership_accepted"] = "execution_ownership_accepted"
    correlation_id: str = Field(min_length=1)
    accepted_by: str = Field(min_length=1)
    evidence_ref: str = Field(min_length=1)
    accepted_at: datetime = Field(default_factory=_utc_now)


class AgentLifecycle(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation_intent_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    state: AgentLifecycleState = "requested"
    history: tuple[LifecycleTransition, ...] = ()
    external_receipts: tuple[ExternalReceiptObservation, ...] = ()

    @model_validator(mode="after")
    def validate_history(self) -> "AgentLifecycle":
        expected_state: AgentLifecycleState = "requested"
        for transition in self.history:
            if transition.from_state != expected_state:
                raise ValueError("lifecycle history is not contiguous")
            if transition.to_state not in ALLOWED_LIFECYCLE_TRANSITIONS[expected_state]:
                raise ValueError("lifecycle history contains an invalid transition")
            expected_state = transition.to_state
        if self.state != expected_state:
            raise ValueError("lifecycle state does not match transition history")
        for observation in self.external_receipts:
            if observation.correlation_id != self.correlation_id:
                raise ValueError("external receipt correlation does not match lifecycle")
        return self


def advance_lifecycle(
    lifecycle: AgentLifecycle,
    to_state: AgentLifecycleState,
    *,
    actor: str,
    reason: str,
    input_ref: str = "",
    output_ref: str = "",
    external_correlation_id: str = "",
) -> AgentLifecycle:
    if to_state == "handoff_accepted":
        raise ValueError(
            "handoff_accepted requires accept_external_handoff_ownership"
        )
    return _advance(
        lifecycle,
        to_state,
        actor=actor,
        reason=reason,
        input_ref=input_ref,
        output_ref=output_ref,
        external_correlation_id=external_correlation_id,
    )


def accept_external_handoff_ownership(
    lifecycle: AgentLifecycle,
    acceptance: ExternalOwnershipAcceptance,
) -> AgentLifecycle:
    if acceptance.correlation_id != lifecycle.correlation_id:
        raise ValueError("ownership acceptance correlation does not match lifecycle")
    matching_receipts = [
        receipt
        for receipt in lifecycle.external_receipts
        if receipt.receipt_id == acceptance.receipt_id
    ]
    if not matching_receipts:
        raise ValueError("ownership acceptance receipt was not observed")
    if matching_receipts[-1].status != acceptance.status:
        raise ValueError("observed receipt does not accept execution ownership")
    return _advance(
        lifecycle,
        "handoff_accepted",
        actor=acceptance.accepted_by,
        reason="external orchestrator accepted execution ownership",
        input_ref=acceptance.receipt_id,
        output_ref=acceptance.evidence_ref,
        external_correlation_id=acceptance.correlation_id,
    )


def record_external_receipt(
    lifecycle: AgentLifecycle,
    *,
    receipt_id: str,
    status: str,
    correlation_id: str,
) -> AgentLifecycle:
    observation = ExternalReceiptObservation(
        receipt_id=receipt_id,
        status=status,
        correlation_id=correlation_id,
    )
    return AgentLifecycle(
        operation_intent_id=lifecycle.operation_intent_id,
        correlation_id=lifecycle.correlation_id,
        state=lifecycle.state,
        history=lifecycle.history,
        external_receipts=(*lifecycle.external_receipts, observation),
    )


def _advance(
    lifecycle: AgentLifecycle,
    to_state: AgentLifecycleState,
    *,
    actor: str,
    reason: str,
    input_ref: str,
    output_ref: str,
    external_correlation_id: str,
) -> AgentLifecycle:
    allowed = ALLOWED_LIFECYCLE_TRANSITIONS[lifecycle.state]
    if to_state not in allowed:
        raise ValueError(
            f"invalid lifecycle transition: {lifecycle.state} -> {to_state}"
        )
    transition = LifecycleTransition(
        from_state=lifecycle.state,
        to_state=to_state,
        actor=actor,
        reason=reason,
        input_ref=input_ref,
        output_ref=output_ref,
        external_correlation_id=external_correlation_id,
    )
    return AgentLifecycle(
        operation_intent_id=lifecycle.operation_intent_id,
        correlation_id=lifecycle.correlation_id,
        state=to_state,
        history=(*lifecycle.history, transition),
        external_receipts=lifecycle.external_receipts,
    )
