from __future__ import annotations

from typing import Any

from app.config.settings import Settings
from app.config.settings import load_settings
from app.providers.openai_provider import build_openai_chat_model


def build_chat_model(settings: Settings | None = None, **kwargs: Any) -> Any:
    resolved_settings = settings or load_settings()
    return build_openai_chat_model(resolved_settings, **kwargs)
