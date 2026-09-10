import json
import pytest

from app.article_processing.finalization import FinalizationError, synthesize_final
from app.article_processing.contracts import AnalysisRequest
from app.article_processing.provider import ProviderBoundaryError, ProviderReply
from tests.test_article_processing_contracts import request_data
from tests.test_article_processing_provider import FakeProvider, LIMIT, execution_control
from tests.test_article_processing_sequential import MemoryStore, request, execute, COMPOSITION


def final(value, fake, store=None, status="running", control=None):
    return synthesize_final(value, provider=fake, composition_limits=COMPOSITION,
                            provider_limits=LIMIT,
                            execution_control=control or execution_control(status=status), store=store)


def test_full_document_provenance_empty_chain_and_repeat_identity():
    value, fake = AnalysisRequest(**request_data()), FakeProvider()
    result = final(value, fake)
    assert result.context_version == 0
    assert result.paragraph_derivation_ids == ()
    assert result.source_content_hash == value.source.content_hash
    assert result.prompt_snapshot_id == value.prompt.prompt_snapshot_id
    assert final(value, fake).candidate_id == result.candidate_id
    assert not hasattr(result, "status")
    assert "synthetic synthesis" not in repr(result)


def test_sequential_synthesizes_all_confirmed_entries_without_mutation():
    store, fake = MemoryStore(), FakeProvider()
    checkpoint = execute(store, fake)
    result = final(request(), fake, store)
    assert result.context_version == 3
    assert len(result.paragraph_derivation_ids) == 3
    data = json.loads(fake.calls[-1][0][4].content)
    assert data["stage"] == "final_synthesis"
    assert len(data["committed_analyses"]) == 3
    assert store.value == checkpoint
    assert store.commits == 3
    assert final(request(), fake, store).candidate_id == result.candidate_id


@pytest.mark.parametrize("status", ["created", "paused", "failed", "cancelled", "superseded", "completed"])
def test_ineligible_run_never_calls_provider(status):
    fake = FakeProvider()
    with pytest.raises(FinalizationError, match="run_not_eligible"):
        final(AnalysisRequest(**request_data()), fake, status=status)
    assert not fake.calls


def test_incomplete_prefix_cannot_produce_synthesis():
    store, fake = MemoryStore(), FakeProvider()
    execute(store, fake)
    store.value = store.value.model_copy(update={"entries": store.value.entries[:1]})
    count = len(fake.calls)
    with pytest.raises(FinalizationError, match="paragraphs_incomplete"):
        final(request(), fake, store)
    assert len(fake.calls) == count


def test_invalid_final_response_preserves_checkpoint():
    store = MemoryStore()
    checkpoint = execute(store, FakeProvider())
    with pytest.raises(ProviderBoundaryError):
        final(request(), FakeProvider(ProviderReply("completed", "invalid")), store)
    assert store.value == checkpoint


def test_missing_store_and_full_document_store_rejected():
    with pytest.raises(FinalizationError, match="checkpoint_required"):
        final(request(), FakeProvider())
    with pytest.raises(FinalizationError, match="full_document_has_no_checkpoint"):
        final(AnalysisRequest(**request_data()), FakeProvider(), MemoryStore())


def test_changed_checkpoint_during_synthesis_fails_closed():
    store = MemoryStore()
    execute(store, FakeProvider())
    class MutatingProvider(FakeProvider):
        def complete(self, messages, **options):
            result = super().complete(messages, **options)
            entry = store.value.entries[-1]
            content = entry.content.model_copy(update={"synthesis": "changed"})
            entries = store.value.entries[:-1] + (entry.model_copy(update={"content": content}),)
            store.value = store.value.model_copy(update={"entries": entries})
            return result
    with pytest.raises(FinalizationError, match="checkpoint_changed"):
        final(request(), MutatingProvider(), store)
