"""Local value contracts, not Bend persistence models or authorization claims."""

from __future__ import annotations

from hashlib import sha256
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(min_length=1, pattern=r"\S")]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
ProcessingMode = Literal["full_document", "sequential_paragraphs"]


def content_hash(text: str) -> str:
    """Hash exact UTF-8 content without silently normalizing the snapshot."""
    return sha256(text.encode("utf-8")).hexdigest()


class ContractValue(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, hide_input_in_errors=True,
        revalidate_instances="always",
    )


class RunScope(ContractValue):
    tenant_id: Identifier
    account_id: Identifier
    user_id: Identifier
    application_id: Identifier


class SourceSnapshot(ContractValue):
    source_snapshot_id: Identifier
    article_id: Identifier
    article_version: Identifier
    content_hash: Digest
    content: str = Field(min_length=1, repr=False)

    @model_validator(mode="after")
    def validate_hash(self) -> SourceSnapshot:
        if content_hash(self.content) != self.content_hash:
            raise ValueError("source_hash_mismatch")
        return self


class PromptSnapshot(ContractValue):
    prompt_snapshot_id: Identifier
    default_prompt_version: Identifier
    selected_profile_id: Identifier = "open-general-analysis"
    selected_profile_version: Identifier
    user_instructions_hash: Digest
    guardrails_version: Identifier
    output_schema_version: Literal["article-analysis-v1"] = "article-analysis-v1"


class Paragraph(ContractValue):
    # Ordinals remain upstream-owned; require order, not an invented start index.
    ordinal: int = Field(ge=0)
    content: str = Field(min_length=1, repr=False)


class ParagraphSequence(ContractValue):
    paragraph_sequence_id: Identifier
    source_snapshot_id: Identifier
    segmentation_version: Identifier
    paragraphs: tuple[Paragraph, ...] = Field(min_length=1, repr=False)

    @model_validator(mode="after")
    def validate_order(self) -> ParagraphSequence:
        ordinals = [item.ordinal for item in self.paragraphs]
        if any(left >= right for left, right in zip(ordinals, ordinals[1:])):
            raise ValueError("paragraph_order_invalid")
        return self


class AnalysisRequest(ContractValue):
    derivation_run_id: Identifier
    scope: RunScope = Field(repr=False)
    source: SourceSnapshot = Field(repr=False)
    processing_mode: ProcessingMode
    prompt: PromptSnapshot
    context_chain_id: Identifier
    idempotency_key: Identifier = Field(repr=False)
    user_analysis_instructions: str = Field(default="", repr=False)
    paragraph_sequence: ParagraphSequence | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def validate_inputs(self) -> AnalysisRequest:
        if content_hash(self.user_analysis_instructions) != self.prompt.user_instructions_hash:
            raise ValueError("instructions_hash_mismatch")
        if self.processing_mode == "full_document":
            if self.paragraph_sequence is not None:
                raise ValueError("full_document_has_no_paragraph_sequence")
        elif self.paragraph_sequence is None:
            raise ValueError("paragraph_sequence_required")
        elif self.paragraph_sequence.source_snapshot_id != self.source.source_snapshot_id:
            raise ValueError("paragraph_source_mismatch")
        return self


class AnalysisContent(ContractValue):
    """Provider content only: never status, scope, tools or persistence commands."""

    schema_version: Literal["article-analysis-v1"] = "article-analysis-v1"
    evidence: tuple[str, ...] = Field(repr=False)
    inferences: tuple[str, ...] = Field(repr=False)
    uncertainties: tuple[str, ...] = Field(repr=False)
    open_questions: tuple[str, ...] = Field(repr=False)
    synthesis: str = Field(min_length=1, repr=False)
