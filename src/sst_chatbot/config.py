import os
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CHAT_MODEL = "gpt-4.1-mini"


def load_jupyter_settings() -> None:
    try:
        from jupyter_settings import SETTINGS
    except ImportError:
        return

    for key, value in SETTINGS.items():
        if value:
            os.environ[key] = value


def load_environment() -> None:
    load_dotenv(ROOT_DIR / ".env")
    load_jupyter_settings()


def require_env(required_keys: Iterable[str]) -> None:
    load_environment()
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    if missing_keys:
        raise RuntimeError(
            "Faltan variables requeridas: "
            + ", ".join(missing_keys)
            + ". Definilas en .env o en jupyter_settings.py."
        )


def validate_runtime_imports() -> None:
    import openai  # noqa: F401
    from langchain_openai import ChatOpenAI  # noqa: F401


def get_default_chat_model() -> str:
    load_environment()
    return os.getenv("OPENAI_CHAT_MODEL", DEFAULT_CHAT_MODEL)
