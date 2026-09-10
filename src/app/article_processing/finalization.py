"""Final synthesis candidates; canonical acceptance remains with Bend."""
from __future__ import annotations

import json
from typing import Literal

from pydantic import Field, ValidationError

from app.article_processing.contracts import (
    AnalysisContent, AnalysisRequest, ContractValue, Digest, Identifier, ProcessingMode, content_hash,
)
from app.article_processing.prompts import CompositionLimits, compose_article_prompt
from app.article_processing.execution import ExecutionControl, ExecutionGuardError, validate_control
from app.article_processing.provider import (
    ArticleProvider, ProviderLimits, analyze_once, analyze_rendered,
)
from app.article_processing.sequential import (
    CheckpointStore, _binding, _validate_checkpoint, context_text,
)
from app.prompts.types import RenderedPromptMessage
from app.prompts.registry import get_prompt_definition


class FinalizationError(ValueError):
    """Fixed safe code only."""


class FinalCandidate(ContractValue):
    # A candidate is not a canonical FINAL_DERIVATION or successful persisted result.
    candidate_id: Digest
    derivation_run_id: Identifier
    article_id: Identifier
    source_snapshot_id: Identifier
    source_content_hash: Digest
    prompt_snapshot_id: Identifier
    processing_mode: ProcessingMode
    context_chain_id: Identifier
    context_version: int = Field(ge=0)
    paragraph_derivation_ids: tuple[str, ...]
    synthesis_policy_version: Literal["article-final-v1"] = "article-final-v1"
    rendered_prompt_hash: Digest
    content: AnalysisContent = Field(repr=False)


def synthesize_final(
    request: AnalysisRequest, *, provider: ArticleProvider,
    composition_limits: CompositionLimits, provider_limits: ProviderLimits,
    execution_control: ExecutionControl, store: CheckpointStore | None = None,
) -> FinalCandidate:
    """Build a candidate only while the owner reports an eligible run.

    No persistence or status transition. Bend must still recheck status
    atomically on acceptance.
    """
    try:
        request = AnalysisRequest.model_validate(request)
        composition_limits = CompositionLimits.model_validate(composition_limits)
        provider_limits = ProviderLimits.model_validate(provider_limits)
    except ValidationError:
        raise FinalizationError("invalid_final_input") from None
    try:
        execution_control = validate_control(execution_control)
    except ValueError:
        raise FinalizationError("invalid_final_input") from None
    binding = _binding(request, composition_limits, provider_limits, execution_control.limits)
    version, refs = 0, ()
    checkpoint_hash = ""
    if request.processing_mode == "full_document":
        if store is not None:
            raise FinalizationError("full_document_has_no_checkpoint")
        try:
            result = analyze_once(
                request, provider=provider, composition_limits=composition_limits,
                provider_limits=provider_limits, execution_control=execution_control,
            )
        except ExecutionGuardError as error:
            raise FinalizationError(str(error)) from None
    else:
        if store is None:
            raise FinalizationError("checkpoint_required")
        try:
            loaded = store.load(request.derivation_run_id)
        except Exception:
            raise FinalizationError("checkpoint_load_failed") from None
        checkpoint = _validate_checkpoint(
            loaded, request, binding, composition_limits.max_context_bytes,
        )
        if checkpoint.version != len(request.paragraph_sequence.paragraphs):
            raise FinalizationError("paragraphs_incomplete")
        # Resolve/validate the pinned prompt using the existing trusted composer.
        # Replace its data layer, never the request identity or immutable source.
        rendered = compose_article_prompt(
            request, limits=composition_limits,
            paragraph_ordinal=request.paragraph_sequence.paragraphs[-1].ordinal,
            bounded_context=context_text(checkpoint),
        )
        messages = list(rendered.messages)
        stage = get_prompt_definition("task.article_final_stage", "1")
        messages[1] = RenderedPromptMessage(role="system", content=stage.messages[0].template)
        messages[4] = RenderedPromptMessage(role="human", content=json.dumps({
            "stage": "final_synthesis", "committed_analyses": json.loads(context_text(checkpoint)),
        }, sort_keys=True, ensure_ascii=True))
        if sum(len(m.content.encode("utf-8")) for m in messages) > composition_limits.max_rendered_bytes:
            raise FinalizationError("final_prompt_limit")
        digest = content_hash(json.dumps(
            {"policy": "article-final-v1", "messages": [m.model_dump() for m in messages]},
            sort_keys=True, ensure_ascii=True,
        ))
        rendered = rendered.model_copy(update={
            "messages": tuple(messages),
            "trace_metadata": rendered.trace_metadata.model_copy(update={"prompt_hash": digest}),
        })
        try:
            result = analyze_rendered(
                rendered, provider=provider, provider_limits=provider_limits,
                execution_control=execution_control, derivation_run_id=request.derivation_run_id,
            )
        except ExecutionGuardError as error:
            raise FinalizationError(str(error)) from None
        # Do not emit a candidate if checkpoint changed during the provider call.
        try:
            observed = store.load(request.derivation_run_id)
        except Exception:
            raise FinalizationError("checkpoint_readback_failed") from None
        observed = _validate_checkpoint(
            observed, request, binding, composition_limits.max_context_bytes,
        )
        if observed != checkpoint:
            raise FinalizationError("checkpoint_changed")
        version = checkpoint.version
        refs = tuple(e.paragraph_derivation_id for e in checkpoint.entries)
        checkpoint_hash = content_hash(context_text(checkpoint))
    identity = content_hash(f"{binding}:article-final-v1:{checkpoint_hash}")
    return FinalCandidate(
        candidate_id=identity, derivation_run_id=request.derivation_run_id,
        article_id=request.source.article_id, source_snapshot_id=request.source.source_snapshot_id,
        source_content_hash=request.source.content_hash, prompt_snapshot_id=request.prompt.prompt_snapshot_id,
        processing_mode=request.processing_mode, context_chain_id=request.context_chain_id,
        context_version=version, paragraph_derivation_ids=refs,
        rendered_prompt_hash=result.prompt_hash, content=result.content,
    )
