from __future__ import annotations

from typing import Any

from app.config.settings import Settings


def build_anthropic_chat_model(settings: Settings, **_: Any) -> Any:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required to initialize Anthropic.")
    raise NotImplementedError(
        "Anthropic adapter is reserved but not enabled because no Anthropic SDK "
        "or LangChain provider package is declared yet."
    )
