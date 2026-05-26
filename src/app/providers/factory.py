from __future__ import annotations

from typing import Any

from app.config.settings import Settings
from app.config.settings import load_settings
from app.providers.anthropic_provider import build_anthropic_chat_model
from app.providers.github_copilot_provider import build_github_copilot_chat_model
from app.providers.openai_provider import build_openai_chat_model


def build_chat_model(settings: Settings | None = None, **kwargs: Any) -> Any:
    resolved_settings = settings or load_settings()
    provider = resolved_settings.agent.provider

    if provider == "openai":
        return build_openai_chat_model(resolved_settings, **kwargs)
    if provider == "anthropic":
        return build_anthropic_chat_model(resolved_settings, **kwargs)
    if provider == "github_copilot":
        return build_github_copilot_chat_model(resolved_settings, **kwargs)

    raise NotImplementedError(
        f"Provider '{provider}' is configured but no adapter is implemented yet."
    )
