from __future__ import annotations

import importlib

from app.config.settings import expected_environment_keys
from app.config.settings import load_settings


def test_settings_module_exposes_expected_environment_keys() -> None:
    assert set(expected_environment_keys()) == {
        "OPENAI_API_KEY",
        "LANGCHAIN_API_KEY",
        "LANGCHAIN_TRACING_V2",
        "LANGCHAIN_PROJECT",
        "LLM_PROVIDER",
        "LLM_MODEL",
        "MEMORY_BACKEND",
        "MEMORY_STRATEGY",
    }


def test_settings_can_read_environment(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("LANGCHAIN_API_KEY", "test-langchain-key")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGCHAIN_PROJECT", "test-project")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-5.5")
    monkeypatch.setenv("LLM_REASONING_EFFORT", "high")
    monkeypatch.setenv("LLM_TEXT_VERBOSITY", "low")
    monkeypatch.setenv("OPENAI_PROMPT_CACHE_RETENTION", "24h")
    monkeypatch.setenv("MEMORY_BACKEND", "openai_responses")
    monkeypatch.setenv("MEMORY_STRATEGY", "previous_response")
    monkeypatch.setenv("MEMORY_STORE_PROVIDER_STATE", "true")

    settings = load_settings()

    assert settings.openai_api_key == "test-openai-key"
    assert settings.langchain_api_key == "test-langchain-key"
    assert settings.langchain_tracing_v2 is True
    assert settings.langchain_project == "test-project"
    assert settings.agent.provider == "openai"
    assert settings.agent.model == "gpt-5.5"
    assert settings.agent.reasoning_effort == "high"
    assert settings.agent.text_verbosity == "low"
    assert settings.agent.prompt_cache_retention == "24h"
    assert settings.agent.memory.backend == "openai_responses"
    assert settings.agent.memory.strategy == "previous_response"
    assert settings.agent.memory.store_provider_state is True


def test_main_module_imports_without_external_calls() -> None:
    module = importlib.import_module("app.main")

    assert callable(module.bootstrap)
