import pytest

from app.article_processing.execution import ExecutionGuardError, ExecutionLimits
from tests.test_article_processing_provider import (
    EXECUTION_LIMIT, FakeProvider, execution_control, invoke,
)


def test_checks_lifecycle_before_and_after_provider_call():
    control = execution_control()
    invoke(FakeProvider(), control)
    assert len(control.lifecycle.calls) == 2
    assert len(control.token_counter.calls) == 1


@pytest.mark.parametrize("status", ["created", "paused", "cancelled", "failed", "completed"])
def test_non_running_state_rejects_before_provider(status):
    provider = FakeProvider()
    with pytest.raises(ExecutionGuardError, match="run_not_eligible"):
        invoke(provider, execution_control(status=status))
    assert provider.calls == []


@pytest.mark.parametrize("count,code", [
    (2049, "input_token_limit"),
    (4000, "input_token_limit"),
])
def test_input_budget_rejects_before_provider(count, code):
    provider = FakeProvider()
    with pytest.raises(ExecutionGuardError, match=code):
        invoke(provider, execution_control(count=count))
    assert provider.calls == []


def test_context_window_reserves_maximum_output():
    limits = ExecutionLimits(
        token_policy_version="fake-token-counter-v1", max_input_tokens=4096,
        max_context_window_tokens=4096,
    )
    provider = FakeProvider()
    with pytest.raises(ExecutionGuardError, match="context_window_limit"):
        invoke(provider, execution_control(count=3841, limits=limits))
    assert provider.calls == []
    invoke(provider, execution_control(count=3840, limits=limits))
    assert len(provider.calls) == 1


@pytest.mark.parametrize("count", [-1, True, "100"])
def test_invalid_counter_result_fails_closed(count):
    with pytest.raises(ExecutionGuardError, match="invalid_token_count"):
        invoke(FakeProvider(), execution_control(count=count))


def test_status_change_during_call_discards_reply():
    control = execution_control()

    class PausingProvider(FakeProvider):
        def complete(self, messages, **options):
            reply = super().complete(messages, **options)
            control.lifecycle.status = "paused"
            return reply

    provider = PausingProvider()
    with pytest.raises(ExecutionGuardError, match="run_not_eligible"):
        invoke(provider, control)
    assert len(provider.calls) == 1


def test_lifecycle_and_counter_failures_are_sanitized():
    class FailedLifecycle:
        def get_status(self, run_id):
            raise RuntimeError("PRIVATE lifecycle")

    class FailedCounter:
        def count(self, messages):
            raise RuntimeError("PRIVATE counter")

    control = execution_control()
    control = type(control)(FailedLifecycle(), control.token_counter, control.limits)
    with pytest.raises(ExecutionGuardError) as lifecycle_error:
        invoke(FakeProvider(), control)
    assert str(lifecycle_error.value) == "lifecycle_read_failed"

    control = execution_control()
    control = type(control)(control.lifecycle, FailedCounter(), control.limits)
    with pytest.raises(ExecutionGuardError) as counter_error:
        invoke(FakeProvider(), control)
    assert str(counter_error.value) == "token_count_failed"


def test_invalid_execution_limits_fail_before_provider():
    provider = FakeProvider()
    invalid = EXECUTION_LIMIT.model_copy(update={"max_input_tokens": True})
    with pytest.raises(ExecutionGuardError, match="invalid_execution_limits"):
        invoke(provider, execution_control(limits=invalid))
    assert provider.calls == []


def test_budget_policy_is_explicit_and_immutable():
    assert EXECUTION_LIMIT.token_policy_version == "fake-token-counter-v1"
