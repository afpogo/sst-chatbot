"""Sequential paragraph execution with a checkpoint port; no finalization."""
from __future__ import annotations

import json
from typing import Protocol

from pydantic import Field, ValidationError

from app.article_processing.contracts import (
    AnalysisContent, AnalysisRequest, ContractValue, Digest, Identifier, content_hash,
)
from app.article_processing.prompts import CompositionLimits
from app.article_processing.provider import ArticleProvider, ProviderLimits, analyze_once


class CheckpointError(ValueError):
    """Fixed safe codes only."""


class CommittedParagraph(ContractValue):
    paragraph_derivation_id: Digest
    derivation_run_id: Identifier
    paragraph_ordinal: int = Field(ge=0)
    input_context_version: int = Field(ge=0)
    prompt_snapshot_id: Identifier
    idempotency_key: Digest
    prompt_hash: Digest
    content: AnalysisContent = Field(repr=False)


class ParagraphCheckpoint(ContractValue):
    derivation_run_id: Identifier
    context_chain_id: Identifier
    binding_hash: Digest
    budget_policy_version: str = "context-prefix-bytes-v1"
    entries: tuple[CommittedParagraph, ...] = Field(default=(), repr=False)

    @property
    def version(self) -> int:
        return len(self.entries)


class CheckpointStore(Protocol):
    def load(self, derivation_run_id: str) -> ParagraphCheckpoint | None:
        """Trusted scoped adapter: callers do not get arbitrary store access."""
        ...

    def commit(self, checkpoint: ParagraphCheckpoint, *, expected_version: int) -> None:
        """Atomically compare version and append exactly one entry, or raise."""
        ...


def _binding(request, composition_limits, provider_limits):
    # Hash only; raw input is never emitted as operational evidence.
    payload = {
        "request": request.model_dump(mode="json"),
        "composition_limits": composition_limits.model_dump(mode="json"),
        "provider_limits": provider_limits.model_dump(mode="json"),
        "budget_policy_version": "context-prefix-bytes-v1",
    }
    return content_hash(json.dumps(payload, sort_keys=True, ensure_ascii=True))


def _entry_key(binding: str, ordinal: int) -> str:
    return content_hash(f"{binding}:paragraph:{ordinal}")


def context_text(checkpoint: ParagraphCheckpoint) -> str:
    """Retain all committed evidence/inference categories and provenance."""
    if not checkpoint.entries:
        return ""
    return json.dumps(
        [entry.model_dump(mode="json") for entry in checkpoint.entries],
        sort_keys=True, ensure_ascii=True, separators=(",", ":"),
    )


def _validate_checkpoint(value, request, binding, limit):
    try:
        value = ParagraphCheckpoint.model_validate(value)
    except ValidationError:
        raise CheckpointError("invalid_checkpoint") from None
    if (value.derivation_run_id != request.derivation_run_id
            or value.context_chain_id != request.context_chain_id
            or value.binding_hash != binding
            or value.budget_policy_version != "context-prefix-bytes-v1"):
        raise CheckpointError("checkpoint_binding_mismatch")
    paragraphs = request.paragraph_sequence.paragraphs
    if value.version > len(paragraphs):
        raise CheckpointError("checkpoint_order_invalid")
    for index, entry in enumerate(value.entries):
        ordinal = paragraphs[index].ordinal
        key = _entry_key(binding, ordinal)
        if (entry.paragraph_ordinal != ordinal or entry.input_context_version != index
                or entry.derivation_run_id != request.derivation_run_id
                or entry.prompt_snapshot_id != request.prompt.prompt_snapshot_id
                or entry.idempotency_key != key or entry.paragraph_derivation_id != key):
            raise CheckpointError("checkpoint_order_invalid")
    if len(context_text(value).encode("utf-8")) > limit:
        raise CheckpointError("context_budget_exceeded")
    return value


def run_paragraphs(
    request: AnalysisRequest, *, provider: ArticleProvider, store: CheckpointStore,
    composition_limits: CompositionLimits, provider_limits: ProviderLimits,
) -> ParagraphCheckpoint:
    """Resume a committed prefix. Return paragraphs only, not a completed run.

    Failures propagate safe codes. A caller may explicitly retry the same request.
    No automatic retries, skipping, context compaction or terminal status changes.
    """
    try:
        request = AnalysisRequest.model_validate(request)
        composition_limits = CompositionLimits.model_validate(composition_limits)
        provider_limits = ProviderLimits.model_validate(provider_limits)
    except ValidationError:
        raise CheckpointError("invalid_execution_input") from None
    if request.processing_mode != "sequential_paragraphs":
        raise CheckpointError("sequential_mode_required")
    binding = _binding(request, composition_limits, provider_limits)
    try:
        loaded = store.load(request.derivation_run_id)
    except Exception:
        raise CheckpointError("checkpoint_load_failed") from None
    checkpoint = loaded if loaded is not None else ParagraphCheckpoint(
        derivation_run_id=request.derivation_run_id, context_chain_id=request.context_chain_id,
        binding_hash=binding,
    )
    checkpoint = _validate_checkpoint(
        checkpoint, request, binding, composition_limits.max_context_bytes,
    )
    for paragraph in request.paragraph_sequence.paragraphs[checkpoint.version:]:
        result = analyze_once(
            request, provider=provider, composition_limits=composition_limits,
            provider_limits=provider_limits, paragraph_ordinal=paragraph.ordinal,
            bounded_context=context_text(checkpoint),
        )
        key = _entry_key(binding, paragraph.ordinal)
        entry = CommittedParagraph(
            paragraph_derivation_id=key, derivation_run_id=request.derivation_run_id,
            paragraph_ordinal=paragraph.ordinal, input_context_version=checkpoint.version,
            prompt_snapshot_id=request.prompt.prompt_snapshot_id,
            idempotency_key=key, prompt_hash=result.prompt_hash, content=result.content,
        )
        candidate = ParagraphCheckpoint(
            derivation_run_id=checkpoint.derivation_run_id,
            context_chain_id=checkpoint.context_chain_id,
            binding_hash=binding, entries=checkpoint.entries + (entry,),
        )
        candidate = _validate_checkpoint(
            candidate, request, binding, composition_limits.max_context_bytes,
        )
        try:
            store.commit(candidate, expected_version=checkpoint.version)
            observed = store.load(request.derivation_run_id)
        except Exception:
            # Commit may have succeeded before a lost acknowledgment: next call reloads.
            raise CheckpointError("checkpoint_commit_unconfirmed") from None
        observed = _validate_checkpoint(
            observed, request, binding, composition_limits.max_context_bytes,
        )
        if observed != candidate:
            raise CheckpointError("checkpoint_readback_mismatch")
        checkpoint = observed
    return checkpoint
