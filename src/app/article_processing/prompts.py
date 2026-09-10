"""Compose private article prompts without provider calls or business effects."""

from __future__ import annotations

import json

from pydantic import Field, ValidationError

from app.article_processing.contracts import AnalysisContent, AnalysisRequest, ContractValue
from app.prompts.renderer import render_prompt
from app.prompts.types import PromptRenderRequest, PromptRenderResult

PROMPT_ID = "task.article_analysis"
PROMPT_VERSION = "1"
PROFILE_ID = "open-general-analysis"


class CompositionError(ValueError):
    """Contains a fixed safe code, never a caller value."""


class CompositionLimits(ContractValue):
    # Caller must supply owner policy: no implicit unlimited or model-token claim.
    max_instructions_bytes: int = Field(gt=0)
    max_source_bytes: int = Field(gt=0)
    max_context_bytes: int = Field(gt=0)
    max_rendered_bytes: int = Field(gt=0)


def _within(text: str, limit: int, code: str) -> None:
    if len(text.encode("utf-8")) > limit:
        raise CompositionError(code)


def compose_article_prompt(
    request: AnalysisRequest,
    *,
    limits: CompositionLimits,
    paragraph_ordinal: int | None = None,
    bounded_context: str = "",
) -> PromptRenderResult:
    """Compose a full-document or single-paragraph call, not the execution loop.

    Sequential context must be supplied by the future verified checkpoint layer.
    The returned render contains private data: only trace_metadata is loggable.
    """
    try:
        request = AnalysisRequest.model_validate(request)
        limits = CompositionLimits.model_validate(limits)
    except ValidationError:
        raise CompositionError("invalid_composition_input") from None
    if not isinstance(bounded_context, str):
        raise CompositionError("invalid_context_type")
    prompt = request.prompt
    if (
        prompt.default_prompt_version != PROMPT_VERSION
        or prompt.guardrails_version != PROMPT_VERSION
        or prompt.selected_profile_version != PROMPT_VERSION
        or prompt.selected_profile_id != PROFILE_ID
    ):
        raise CompositionError("unsupported_prompt_snapshot")
    if request.processing_mode == "full_document":
        if paragraph_ordinal is not None or bounded_context:
            raise CompositionError("full_document_context_not_empty")
        content = request.source.content
    else:
        if type(paragraph_ordinal) is not int:
            raise CompositionError("paragraph_ordinal_required")
        content = next(
            (item.content for item in request.paragraph_sequence.paragraphs
             if item.ordinal == paragraph_ordinal), None,
        )
        if content is None:
            raise CompositionError("paragraph_not_in_snapshot")
    _within(request.user_analysis_instructions, limits.max_instructions_bytes, "instructions_limit")
    _within(content, limits.max_source_bytes, "source_limit")
    _within(bounded_context, limits.max_context_bytes, "context_limit")
    payload = {
        "processing_mode": request.processing_mode,
        "paragraph_ordinal": paragraph_ordinal,
        "content": content,
        "context": bounded_context,
    }
    # JSON delimitation preserves arbitrary user text as data, not a template.
    # It is not a claim that the model is universally immune to prompt injection.
    try:
        rendered = render_prompt(PromptRenderRequest(
            prompt_id=PROMPT_ID, version=PROMPT_VERSION,
            variables={
                "instructions_json": json.dumps(request.user_analysis_instructions, ensure_ascii=False),
                "source_json": json.dumps(payload, ensure_ascii=False),
                "output_schema": json.dumps(AnalysisContent.model_json_schema(), sort_keys=True),
            },
        ))
    except (ValueError, KeyError):
        raise CompositionError("prompt_render_failed") from None
    _within(
        "".join(message.content for message in rendered.messages),
        limits.max_rendered_bytes, "rendered_limit",
    )
    return rendered
