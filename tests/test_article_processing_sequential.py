import json

import pytest

from app.article_processing.contracts import AnalysisRequest, content_hash
from app.article_processing.provider import ProviderReply, ProviderBoundaryError
from app.article_processing.sequential import CheckpointError, context_text, run_paragraphs
from tests.test_article_processing_contracts import request_data, sequence
from tests.test_article_processing_prompts import LIMITS
from tests.test_article_processing_provider import FakeProvider, LIMIT, execution_control

COMPOSITION = LIMITS.model_copy(update={"max_context_bytes": 16000, "max_rendered_bytes": 30000})


class MemoryStore:
    """Test fake only; no restart durability or authorization claim."""
    def __init__(self):
        self.value = None
        self.commits = 0
        self.fail_before = False
        self.fail_after = False

    def load(self, run_id):
        return self.value

    def commit(self, checkpoint, *, expected_version):
        if self.fail_before:
            raise RuntimeError("private store detail")
        current = self.value.version if self.value else 0
        if current != expected_version or checkpoint.version != current + 1:
            raise RuntimeError("conflict")
        self.value = checkpoint
        self.commits += 1
        if self.fail_after:
            self.fail_after = False
            raise RuntimeError("ack lost")


def request():
    return AnalysisRequest(**(request_data() | {
        "processing_mode": "sequential_paragraphs", "paragraph_sequence": sequence(),
    }))


def execute(store, provider, value=None, limits=COMPOSITION, control=None):
    return run_paragraphs(value or request(), provider=provider, store=store,
                          composition_limits=limits, provider_limits=LIMIT,
                          execution_control=control or execution_control())


def test_order_context_and_reentry_without_duplicate_calls():
    store, provider = MemoryStore(), FakeProvider()
    checkpoint = execute(store, provider)
    assert checkpoint.version == 3
    assert [e.paragraph_ordinal for e in checkpoint.entries] == [1, 2, 3]
    assert [e.input_context_version for e in checkpoint.entries] == [0, 1, 2]
    assert len({e.idempotency_key for e in checkpoint.entries}) == 3
    for index, (messages, _) in enumerate(provider.calls):
        payload = json.loads(messages[4].content.split("\n", 1)[1])
        assert payload["paragraph_ordinal"] == index + 1
        prior = json.loads(payload["context"]) if payload["context"] else []
        assert len(prior) == index
    assert execute(store, provider) == checkpoint
    assert len(provider.calls) == store.commits == 3
    assert not hasattr(checkpoint, "final_derivation")
    assert "synthetic synthesis" not in repr(checkpoint)


def test_provider_failure_preserves_prefix_and_retry_resumes():
    store = MemoryStore()
    class FailSecond(FakeProvider):
        def complete(self, messages, **options):
            result = super().complete(messages, **options)
            if len(self.calls) == 2:
                return ProviderReply("completed", "invalid")
            return result
    provider = FailSecond()
    with pytest.raises(ProviderBoundaryError):
        execute(store, provider)
    assert store.value.version == 1
    key = store.value.entries[0].idempotency_key
    execute(store, provider)
    assert store.value.version == 3
    assert store.value.entries[0].idempotency_key == key
    assert len(provider.calls) == 4


def test_unconfirmed_commit_stops_before_next_paragraph_and_recovers():
    store, provider = MemoryStore(), FakeProvider()
    store.fail_after = True
    with pytest.raises(CheckpointError, match="checkpoint_commit_unconfirmed"):
        execute(store, provider)
    assert store.value.version == 1
    assert len(provider.calls) == 1
    execute(store, provider)
    assert len(provider.calls) == 3


def test_failed_write_never_advances():
    store, provider = MemoryStore(), FakeProvider()
    store.fail_before = True
    with pytest.raises(CheckpointError, match="checkpoint_commit_unconfirmed"):
        execute(store, provider)
    assert store.value is None
    assert len(provider.calls) == 1


@pytest.mark.parametrize("kind", ["scope", "prompt", "source", "budget", "token"])
def test_same_run_cannot_mix_binding(kind):
    store, provider = MemoryStore(), FakeProvider()
    execute(store, provider)
    value = request()
    limits = COMPOSITION
    control = execution_control()
    if kind == "scope":
        value = value.model_copy(update={"scope": value.scope.model_copy(update={"tenant_id": "other"})})
    elif kind == "prompt":
        value = value.model_copy(update={"prompt": value.prompt.model_copy(update={"prompt_snapshot_id": "other"})})
    elif kind == "source":
        source = value.source.model_copy(update={"content": "different", "content_hash": content_hash("different")})
        value = value.model_copy(update={"source": source})
    elif kind == "budget":
        limits = COMPOSITION.model_copy(update={"max_context_bytes": 15999})
    else:
        token_limits = control.limits.model_copy(update={"max_input_tokens": 2047})
        control = execution_control(limits=token_limits)
    with pytest.raises(CheckpointError, match="checkpoint_binding_mismatch"):
        execute(store, provider, value, limits, control)
    assert len(provider.calls) == 3


def test_budget_failure_preserves_confirmed_prefix_without_truncation():
    store, provider = MemoryStore(), FakeProvider()
    # First obtain the exact fake checkpoint size, then execute a separate store.
    execute(store, provider)
    one = store.value.model_copy(update={"entries": store.value.entries[:1]})
    limits = COMPOSITION.model_copy(update={"max_context_bytes": len(context_text(one).encode()) + 50})
    store, provider = MemoryStore(), FakeProvider()
    with pytest.raises(CheckpointError, match="context_budget_exceeded"):
        execute(store, provider, limits=limits)
    assert store.value.version == 1
    assert len(provider.calls) == 2


def test_corrupt_checkpoint_order_rejected_before_provider():
    store, provider = MemoryStore(), FakeProvider()
    execute(store, provider)
    store.value = store.value.model_copy(update={"entries": tuple(reversed(store.value.entries))})
    with pytest.raises(CheckpointError, match="checkpoint_order_invalid"):
        execute(store, provider)
    assert len(provider.calls) == 3


def test_full_document_not_sent_through_sequential_runner():
    with pytest.raises(CheckpointError, match="sequential_mode_required"):
        execute(MemoryStore(), FakeProvider(), AnalysisRequest(**request_data()))


def test_failed_load_is_sanitized_without_provider_call():
    class BadStore(MemoryStore):
        def load(self, run_id):
            raise RuntimeError("private store details")
    provider = FakeProvider()
    with pytest.raises(CheckpointError, match="checkpoint_load_failed"):
        execute(BadStore(), provider)
    assert provider.calls == []


def test_noop_commit_does_not_advance_without_readback():
    class NoopStore(MemoryStore):
        def commit(self, checkpoint, *, expected_version):
            pass
    provider = FakeProvider()
    with pytest.raises(CheckpointError, match="invalid_checkpoint"):
        execute(NoopStore(), provider)
    assert len(provider.calls) == 1


def test_fake_compare_and_swap_rejects_stale_commit():
    store = MemoryStore()
    execute(store, FakeProvider())
    with pytest.raises(RuntimeError, match="conflict"):
        store.commit(store.value, expected_version=0)
    assert store.value.version == 3
