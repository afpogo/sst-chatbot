from __future__ import annotations

from app.config.settings import Settings
from app.config.settings import load_settings


def bootstrap() -> Settings:
    return load_settings()


def main() -> int:
    settings = bootstrap()
    print(
        "Configuration loaded for "
        f"{settings.agent.provider}:{settings.agent.model} "
        f"in LangChain project {settings.langchain_project}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
