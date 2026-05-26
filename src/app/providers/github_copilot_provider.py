from __future__ import annotations

from typing import Any

from app.config.settings import Settings


def build_github_copilot_chat_model(settings: Settings, **_: Any) -> Any:
    if not settings.github_copilot_api_key:
        raise RuntimeError(
            "GITHUB_COPILOT_API_KEY is required to initialize GitHub Copilot."
        )
    raise NotImplementedError(
        "GitHub Copilot adapter is reserved until this repo defines a supported "
        "API boundary and dependency for programmatic model calls."
    )
