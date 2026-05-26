from __future__ import annotations

import pytest

from app.config.settings import Settings
from app.providers.factory import build_chat_model
from app.providers.model_registry import get_model_profile
from app.providers.openai_provider import build_openai_responses_options
from app.providers.types import AgentRuntimeConfig
from app.providers.types import MemoryConfig


def test_openai_model_profile_exposes_reasoning_and_memory_capabilities() -> None:
    profile = get_model_profile("openai", "gpt-5.5")

    assert profile.supports_reasoning_effort is True
    assert profile.default_reasoning_effort == "medium"
    assert profile.default_prompt_cache_retention == "24h"
    assert profile.supports_previous_response_id is True
    assert profile.supports_conversations_api is True


def test_openai_default_development_model_uses_in_memory_cache() -> None:
    profile = get_model_profile("openai", "gpt-5.4-mini")

    assert profile.supports_prompt_cache_retention is True
    assert profile.default_prompt_cache_retention == "in_memory"


def test_custom_model_profile_does_not_assume_capabilities() -> None:
    profile = get_model_profile("local", "local-test-model")

    assert profile.family == "custom"
    assert profile.supports_reasoning_effort is False
    assert profile.supports_previous_response_id is False


def test_openai_responses_options_are_derived_from_config() -> None:
    config = AgentRuntimeConfig(
        provider="openai",
        model="gpt-5.5",
        reasoning_effort="high",
        text_verbosity="low",
        prompt_cache_retention="auto",
        memory=MemoryConfig(
            backend="openai_responses",
            strategy="previous_response",
            store_provider_state=True,
            previous_response_id="resp_123",
        ),
    )

    options = build_openai_responses_options(config)

    assert options == {
        "model": "gpt-5.5",
        "reasoning": {"effort": "high"},
        "text": {"verbosity": "low"},
        "prompt_cache_retention": "24h",
        "store": True,
        "previous_response_id": "resp_123",
    }


def test_factory_rejects_provider_without_adapter() -> None:
    settings = Settings(agent=AgentRuntimeConfig(provider="local", model="test"))

    with pytest.raises(NotImplementedError, match="no adapter"):
        build_chat_model(settings)
