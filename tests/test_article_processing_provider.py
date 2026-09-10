import json
import traceback

import pytest

from app.article_processing.provider import (
    ProviderBoundaryError, ProviderLimits, ProviderReply, analyze_once, parse_analysis_reply,
)
from app.article_processing.execution import ExecutionControl, ExecutionLimits
from tests.test_article_processing_prompts import LIMITS, request

LIMIT = ProviderLimits(max_response_bytes=4096, max_output_tokens=256, timeout_seconds=3)
EXECUTION_LIMIT = ExecutionLimits(
    token_policy_version="fake-token-counter-v1", max_input_tokens=2048,
    max_context_window_tokens=4096,
)
PAYLOAD = dict(schema_version="article-analysis-v1", evidence=["synthetic evidence"],
               inferences=[], uncertainties=[], open_questions=[], synthesis="synthetic synthesis")


class FakeProvider:
    def __init__(self, reply=None, error=None):
        self.reply = reply if reply is not None else ProviderReply("completed", json.dumps(PAYLOAD))
        self.error = error
        self.calls = []

    def complete(self, messages, **options):
        self.calls.append((messages, options))
        if self.error:
            raise self.error
        return self.reply


class FakeLifecycle:
    def __init__(self, status="running"):
        self.status = status
        self.calls = []

    def get_status(self, run_id):
        self.calls.append(run_id)
        return self.status


class FakeTokenCounter:
    def __init__(self, count=100):
        self.value = count
        self.calls = []

    def count(self, messages):
        self.calls.append(messages)
        return self.value


def execution_control(status="running", count=100, limits=EXECUTION_LIMIT):
    return ExecutionControl(FakeLifecycle(status), FakeTokenCounter(count), limits)


def invoke(fake, control=None):
    return analyze_once(
        request(), provider=fake, composition_limits=LIMITS, provider_limits=LIMIT,
        execution_control=control or execution_control(),
    )


def test_valid_content_and_explicit_limits_without_scope():
    fake = FakeProvider()
    result = invoke(fake)
    assert result.content.evidence == ("synthetic evidence",)
    assert result.content.synthesis == PAYLOAD["synthesis"]
    messages, options = fake.calls[0]
    assert len(messages) == 6
    assert options == {"max_output_tokens": 256, "timeout_seconds": 3}
    assert len(result.prompt_hash) == 64
    assert not hasattr(result, "status")
    assert "synthetic synthesis" not in repr(result)
    assert "private source" not in repr(messages)


@pytest.mark.parametrize("text", [
    "not json", "[]", "null", '""', "{}", chr(96) * 3 + "json",
    json.dumps(PAYLOAD) + "{}",
    json.dumps(PAYLOAD)[:-1] + ', "schema_version": "article-analysis-v1"}',
    json.dumps(PAYLOAD | {"accept_memory": True}),
    json.dumps(PAYLOAD | {"synthesis": 1}),
    json.dumps(PAYLOAD | {"synthesis": "  "}),
    json.dumps(PAYLOAD | {"evidence": "not an array"}),
    json.dumps(PAYLOAD | {"evidence": [True]}),
    json.dumps(PAYLOAD | {"evidence": [" "]}),
    json.dumps(PAYLOAD | {"schema_version": "other"}),
    json.dumps({k: v for k, v in PAYLOAD.items() if k != "schema_version"}),
    '{"synthesis": NaN}',
])
def test_rejects_malformed_or_authoritative_output(text):
    with pytest.raises(ProviderBoundaryError, match="invalid_provider_output"):
        parse_analysis_reply(text, max_response_bytes=4096)


@pytest.mark.parametrize("status,code", [
    ("truncated", "provider_truncated"), ("refused", "provider_refused"),
    ("unknown", "invalid_provider_reply"),
])
def test_noncompletion_never_returns_content(status, code):
    fake = FakeProvider(ProviderReply(status, json.dumps(PAYLOAD)))
    with pytest.raises(ProviderBoundaryError, match=code):
        invoke(fake)
    assert len(fake.calls) == 1


@pytest.mark.parametrize("error,code", [
    (TimeoutError("PRIVATE timeout"), "provider_timeout"),
    (RuntimeError("PRIVATE credentials"), "provider_failure"),
])
def test_errors_sanitized_without_retry(error, code):
    fake = FakeProvider(error=error)
    with pytest.raises(ProviderBoundaryError) as exc:
        invoke(fake)
    assert str(exc.value) == code
    assert "PRIVATE" not in "".join(traceback.format_exception(exc.type, exc.value, exc.tb))
    assert len(fake.calls) == 1


def test_input_failure_does_not_call_provider():
    fake = FakeProvider()
    with pytest.raises(ProviderBoundaryError, match="invalid_analysis_input"):
        analyze_once(request(), provider=fake,
                     composition_limits=LIMITS.model_copy(update={"max_source_bytes": 1}),
                     provider_limits=LIMIT, execution_control=execution_control())
    assert fake.calls == []


def test_response_limit_and_unicode_errors():
    raw = json.dumps(PAYLOAD)
    assert parse_analysis_reply(raw, max_response_bytes=len(raw.encode())).synthesis
    with pytest.raises(ProviderBoundaryError, match="provider_output_limit"):
        parse_analysis_reply(raw, max_response_bytes=len(raw.encode()) - 1)
    for value in (b"bytes", "\ud800"):
        with pytest.raises(ProviderBoundaryError, match="invalid_provider_output"):
            parse_analysis_reply(value, max_response_bytes=4096)


def test_invalid_limits_and_reply_type():
    fake = FakeProvider()
    with pytest.raises(ProviderBoundaryError, match="invalid_provider_limits"):
        analyze_once(request(), provider=fake, composition_limits=LIMITS,
                     provider_limits=LIMIT.model_copy(update={"max_output_tokens": True}),
                     execution_control=execution_control())
    assert fake.calls == []
    with pytest.raises(ProviderBoundaryError, match="invalid_provider_reply"):
        invoke(FakeProvider(reply="not a reply"))


def test_oversize_reply_never_returns_result():
    with pytest.raises(ProviderBoundaryError, match="provider_output_limit"):
        invoke(FakeProvider(ProviderReply("completed", "private" * 1000)))
