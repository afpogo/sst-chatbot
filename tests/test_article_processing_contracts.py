from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.article_processing.contracts import (
    AnalysisContent, AnalysisRequest, Paragraph, ParagraphSequence,
    PromptSnapshot, RunScope, SourceSnapshot, content_hash,
)


def request_data():
    return dict(
        derivation_run_id="run-1",
        scope=RunScope(tenant_id="tenant", account_id="account", user_id="user", application_id="sst"),
        source=SourceSnapshot(source_snapshot_id="source-1", article_id="article-1",
                              article_version="1", content_hash=content_hash("private source"),
                              content="private source"),
        processing_mode="full_document",
        prompt=PromptSnapshot(prompt_snapshot_id="prompt-1", default_prompt_version="1",
                              selected_profile_version="1", guardrails_version="1",
                              user_instructions_hash=content_hash("")),
        context_chain_id="chain-1", idempotency_key="key-1",
    )


def sequence(ordinals=(1, 2, 3), source="source-1"):
    return ParagraphSequence(
        paragraph_sequence_id="seq-1", source_snapshot_id=source, segmentation_version="1",
        paragraphs=tuple(Paragraph(ordinal=n, content="private paragraph") for n in ordinals),
    )


def test_full_document_and_sequential_requests():
    data = request_data()
    assert AnalysisRequest(**data).paragraph_sequence is None
    data.update(processing_mode="sequential_paragraphs", paragraph_sequence=sequence())
    assert len(AnalysisRequest(**data).paragraph_sequence.paragraphs) == 3


@pytest.mark.parametrize("ordinals", [(1, 1), (2, 1), ()])
def test_sequence_rejects_duplicate_unordered_and_empty(ordinals):
    with pytest.raises(ValidationError):
        sequence(ordinals)


@pytest.mark.parametrize("changes", [
    {"processing_mode": "hybrid"},
    {"processing_mode": "sequential_paragraphs"},
    {"paragraph_sequence": sequence()},
    {"processing_mode": "sequential_paragraphs", "paragraph_sequence": sequence(source="other")},
    {"user_analysis_instructions": "changed"},
    {"accept_memory": True},
])
def test_request_rejects_inconsistent_or_extra_inputs(changes):
    with pytest.raises(ValidationError):
        AnalysisRequest(**(request_data() | changes))


def test_prompt_version_and_scope_are_immutable():
    request = AnalysisRequest(**request_data())
    with pytest.raises(ValidationError):
        request.prompt.selected_profile_version = "2"
    with pytest.raises(ValidationError):
        request.scope.tenant_id = "other"


def test_hash_uses_exact_content_and_error_repr_hides_inputs():
    assert content_hash("a\n") != content_hash("a")
    with pytest.raises(ValidationError) as exc:
        SourceSnapshot(source_snapshot_id="s", article_id="a", article_version="1",
                       content_hash=content_hash("other"), content="private source")
    assert "private source" not in str(exc.value)
    assert "private source" not in repr(AnalysisRequest(**request_data()))


def test_content_has_no_authority_and_is_not_log_payload():
    data = dict(evidence=("private evidence",), inferences=(), uncertainties=(),
                open_questions=(), synthesis="private synthesis")
    output = AnalysisContent(**data)
    assert "private" not in repr(output)
    with pytest.raises(ValidationError):
        AnalysisContent(**data, status="accepted")
    with pytest.raises(ValidationError):
        AnalysisContent(**(data | {"schema_version": "other"}))


def test_strict_types_and_nested_copy_bypass_are_revalidated():
    with pytest.raises(ValidationError):
        Paragraph(ordinal=True, content="paragraph")
    data = request_data()
    data["source"] = data["source"].model_copy(update={"content": "tampered"})
    with pytest.raises(ValidationError):
        AnalysisRequest(**data)


def test_owner_spec_is_indexed_and_evidence_exists():
    root = Path(__file__).resolve().parents[1]
    path = "specs/architecture/article-processing-pipeline.yaml"
    spec = yaml.safe_load((root / path).read_text(encoding="utf-8"))
    index = yaml.safe_load((root / "specs/00-index.yaml").read_text(encoding="utf-8"))
    assert any(entry["path"] == path for entry in index["entries"]["architecture"])
    assert spec["implementation_status"] == "execution-guard-local"
    for ref in spec["local_evidence"]:
        assert (root / ref).is_file()
