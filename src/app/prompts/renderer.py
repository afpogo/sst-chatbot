from __future__ import annotations

import hashlib
import json
from time import perf_counter

from app.prompts.registry import get_prompt_definition
from app.prompts.types import PromptDefinition
from app.prompts.types import PromptRenderRequest
from app.prompts.types import PromptRenderResult
from app.prompts.types import PromptTraceMetadata
from app.prompts.types import RenderedPromptMessage
from app.prompts.validators import validate_render_variables


def render_prompt(request: PromptRenderRequest) -> PromptRenderResult:
    started_at = perf_counter()
    prompt = get_prompt_definition(request.prompt_id, request.version)
    variables = validate_render_variables(prompt, request.variables)
    messages = tuple(
        RenderedPromptMessage(
            role=message.role,
            content=message.template.format(**variables),
        )
        for message in prompt.messages
    )

    return PromptRenderResult(
        prompt=prompt,
        messages=messages,
        trace_metadata=_build_trace_metadata(
            prompt=prompt,
            messages=messages,
            provider=request.provider,
            model=request.model,
            variable_names=tuple(sorted(variables)),
            render_ms=(perf_counter() - started_at) * 1000,
        ),
    )


def _build_trace_metadata(
    prompt: PromptDefinition,
    messages: tuple[RenderedPromptMessage, ...],
    provider: str,
    model: str,
    variable_names: tuple[str, ...],
    render_ms: float,
) -> PromptTraceMetadata:
    hash_payload = {
        "prompt_id": prompt.id,
        "prompt_version": prompt.version,
        "messages": [message.model_dump() for message in messages],
    }
    prompt_hash = hashlib.sha256(
        json.dumps(hash_payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()

    return PromptTraceMetadata(
        prompt_id=prompt.id,
        prompt_version=prompt.version,
        prompt_hash=prompt_hash,
        provider=provider,
        model=model,
        trace_policy=prompt.trace_policy,
        provider_cache_policy=prompt.provider_cache_policy,
        visibility=prompt.visibility,
        variable_names=variable_names,
        render_ms=render_ms,
    )
