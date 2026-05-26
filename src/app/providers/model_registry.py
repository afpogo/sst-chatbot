from __future__ import annotations

from app.providers.types import ModelProfile
from app.providers.types import ProviderName

OPENAI_DOCS_MODELS_URL = "https://developers.openai.com/api/docs/models"
OPENAI_DOCS_LATEST_MODEL_URL = "https://developers.openai.com/api/docs/guides/latest-model"
OPENAI_DOCS_CONVERSATION_STATE_URL = (
    "https://developers.openai.com/api/docs/guides/conversation-state"
)
OPENAI_DOCS_PROMPT_CACHING_URL = (
    "https://developers.openai.com/api/docs/guides/prompt-caching"
)

OPENAI_MODEL_PROFILES: dict[str, ModelProfile] = {
    "gpt-5.5": ModelProfile(
        provider="openai",
        model="gpt-5.5",
        family="gpt-5",
        recommended_for=(
            "complex reasoning",
            "coding",
            "tool-heavy agents",
            "long-context retrieval",
        ),
        supports_reasoning_effort=True,
        supported_reasoning_efforts=("none", "low", "medium", "high", "xhigh"),
        default_reasoning_effort="medium",
        supports_text_verbosity=True,
        supports_prompt_cache_retention=True,
        default_prompt_cache_retention="24h",
        supports_previous_response_id=True,
        supports_conversations_api=True,
        context_window_tokens=1_000_000,
        max_output_tokens=128_000,
        source_url=OPENAI_DOCS_LATEST_MODEL_URL,
        notes="Recommended OpenAI frontier model for complex production workflows.",
    ),
    "gpt-5.4": ModelProfile(
        provider="openai",
        model="gpt-5.4",
        family="gpt-5",
        recommended_for=("coding", "professional work", "agentic tasks"),
        supports_reasoning_effort=True,
        supported_reasoning_efforts=("none", "low", "medium", "high", "xhigh"),
        default_reasoning_effort="medium",
        supports_text_verbosity=True,
        supports_prompt_cache_retention=True,
        default_prompt_cache_retention="in_memory",
        supports_previous_response_id=True,
        supports_conversations_api=True,
        context_window_tokens=1_000_000,
        max_output_tokens=128_000,
        source_url=OPENAI_DOCS_MODELS_URL,
        notes="More affordable OpenAI frontier model for coding and professional work.",
    ),
    "gpt-5.4-mini": ModelProfile(
        provider="openai",
        model="gpt-5.4-mini",
        family="gpt-5",
        recommended_for=("cost-efficient agents", "well-defined tasks", "subagents"),
        supports_reasoning_effort=True,
        supported_reasoning_efforts=("none", "low", "medium", "high", "xhigh"),
        default_reasoning_effort="medium",
        supports_text_verbosity=True,
        supports_prompt_cache_retention=True,
        default_prompt_cache_retention="in_memory",
        supports_previous_response_id=True,
        supports_conversations_api=True,
        context_window_tokens=400_000,
        max_output_tokens=128_000,
        source_url=OPENAI_DOCS_MODELS_URL,
        notes="Default repo model for cost-sensitive local development.",
    ),
    "gpt-4.1": ModelProfile(
        provider="openai",
        model="gpt-4.1",
        family="gpt-4.1",
        recommended_for=("non-reasoning chat", "lower orchestration complexity"),
        supports_prompt_cache_retention=True,
        default_prompt_cache_retention="in_memory",
        supports_previous_response_id=True,
        supports_conversations_api=True,
        source_url=OPENAI_DOCS_MODELS_URL,
        notes="Non-reasoning model family; keep reasoning parameters disabled.",
    ),
}

_MODEL_PROFILES = {
    ("openai", model): profile for model, profile in OPENAI_MODEL_PROFILES.items()
}


def get_model_profile(provider: ProviderName, model: str) -> ModelProfile:
    profile = _MODEL_PROFILES.get((provider, model))
    if profile:
        return profile

    return ModelProfile(
        provider=provider,
        model=model,
        family="custom",
        source_url="",
        notes="Custom or unregistered model. Capabilities must be validated before production use.",
    )
