from __future__ import annotations

from typing import Any

from app.config.settings import Settings
from app.providers.model_registry import get_model_profile
from app.providers.types import AgentRuntimeConfig
from app.prompts.types import PromptTraceMetadata


def build_openai_chat_model(settings: Settings, **kwargs: Any) -> Any:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to initialize OpenAI.")

    from langchain_openai import ChatOpenAI

    model_kwargs: dict[str, Any] = {
        "api_key": settings.openai_api_key,
        "model": settings.agent.model,
        **kwargs,
    }
    if settings.agent.temperature is not None:
        model_kwargs["temperature"] = settings.agent.temperature
    if settings.agent.max_output_tokens is not None:
        model_kwargs["max_tokens"] = settings.agent.max_output_tokens

    return ChatOpenAI(**model_kwargs)


def build_openai_responses_options(
    config: AgentRuntimeConfig,
    prompt_metadata: PromptTraceMetadata | None = None,
) -> dict[str, Any]:
    profile = get_model_profile("openai", config.model)
    options: dict[str, Any] = {"model": config.model}

    if profile.supports_reasoning_effort:
        options["reasoning"] = {"effort": config.reasoning_effort}
    if profile.supports_text_verbosity:
        options["text"] = {"verbosity": config.text_verbosity}
    if profile.supports_prompt_cache_retention:
        retention = _resolve_prompt_cache_retention(config, prompt_metadata)
        if retention is not None:
            options["prompt_cache_retention"] = retention

    memory = config.memory
    if memory.backend == "openai_responses":
        options["store"] = memory.store_provider_state
        if memory.strategy == "previous_response" and memory.previous_response_id:
            options["previous_response_id"] = memory.previous_response_id
    if memory.backend == "openai_conversations" and memory.conversation_id:
        options["conversation"] = memory.conversation_id

    return options


def _resolve_prompt_cache_retention(
    config: AgentRuntimeConfig,
    prompt_metadata: PromptTraceMetadata | None,
) -> str | None:
    if prompt_metadata is not None:
        if prompt_metadata.provider_cache_policy == "none":
            return None
        return prompt_metadata.provider_cache_policy

    profile = get_model_profile("openai", config.model)
    retention = config.prompt_cache_retention
    if retention == "auto":
        return profile.default_prompt_cache_retention
    return retention
