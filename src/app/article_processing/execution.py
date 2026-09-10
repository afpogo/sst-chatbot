"""Fail-closed lifecycle and input-budget checks for provider calls."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from pydantic import Field, ValidationError

from app.article_processing.contracts import ContractValue


class ExecutionGuardError(ValueError):
    """Fixed safe codes only; adapters must not leak owner/provider details."""


class RunLifecyclePort(Protocol):
    def get_status(self, derivation_run_id: str) -> str:
        """Read the authoritative current status for exactly one scoped run."""
        ...


class CountableMessage(Protocol):
    role: str
    content: str


class InputTokenCounter(Protocol):
    def count(self, messages: Sequence[CountableMessage]) -> int:
        """Return the adapter/model-specific token count for rendered messages."""
        ...


class ExecutionLimits(ContractValue):
    token_policy_version: str = Field(min_length=1, pattern=r"\S")
    max_input_tokens: int = Field(gt=0)
    max_context_window_tokens: int = Field(gt=0)


@dataclass(frozen=True)
class ExecutionControl:
    lifecycle: RunLifecyclePort
    token_counter: InputTokenCounter
    limits: ExecutionLimits


def validate_control(control: ExecutionControl) -> ExecutionControl:
    if not isinstance(control, ExecutionControl):
        raise ExecutionGuardError("invalid_execution_control")
    try:
        limits = ExecutionLimits.model_validate(control.limits)
    except ValidationError:
        raise ExecutionGuardError("invalid_execution_limits") from None
    return ExecutionControl(control.lifecycle, control.token_counter, limits)


def _assert_running(control: ExecutionControl, derivation_run_id: str) -> None:
    try:
        status = control.lifecycle.get_status(derivation_run_id)
    except Exception:
        raise ExecutionGuardError("lifecycle_read_failed") from None
    if status != "running":
        raise ExecutionGuardError("run_not_eligible")


def authorize_provider_call(
    control: ExecutionControl, *, derivation_run_id: str,
    messages: Sequence[CountableMessage], max_output_tokens: int,
) -> None:
    """Check fresh lifecycle state and the model-specific context budget."""
    control = validate_control(control)
    _assert_running(control, derivation_run_id)
    try:
        count = control.token_counter.count(messages)
    except Exception:
        raise ExecutionGuardError("token_count_failed") from None
    if type(count) is not int or count < 0:
        raise ExecutionGuardError("invalid_token_count")
    if count > control.limits.max_input_tokens:
        raise ExecutionGuardError("input_token_limit")
    if count + max_output_tokens > control.limits.max_context_window_tokens:
        raise ExecutionGuardError("context_window_limit")


def confirm_provider_call(control: ExecutionControl, *, derivation_run_id: str) -> None:
    """Reject an answer when the run stopped while the provider was working."""
    _assert_running(validate_control(control), derivation_run_id)
