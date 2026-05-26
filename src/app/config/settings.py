from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic import Field

from app.providers.types import AgentRuntimeConfig
from app.providers.types import MemoryConfig

ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_LANGCHAIN_PROJECT = "agentic-python-lab"
DEFAULT_LLM_PROVIDER = "openai"
DEFAULT_LLM_MODEL = "gpt-5.4-mini"


class Settings(BaseModel):
    openai_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")
    github_copilot_api_key: str = Field(default="")
    deepseek_api_key: str = Field(default="")
    langchain_api_key: str = Field(default="")
    langchain_tracing_v2: bool = Field(default=False)
    langchain_project: str = Field(default=DEFAULT_LANGCHAIN_PROJECT)
    agent: AgentRuntimeConfig = Field(default_factory=AgentRuntimeConfig)


def expected_environment_keys() -> tuple[str, ...]:
    return (
        "OPENAI_API_KEY",
        "LANGCHAIN_API_KEY",
        "LANGCHAIN_TRACING_V2",
        "LANGCHAIN_PROJECT",
        "LLM_PROVIDER",
        "LLM_MODEL",
        "MEMORY_BACKEND",
        "MEMORY_STRATEGY",
    )


def load_settings(env_file: Path | None = None, override: bool = False) -> Settings:
    dotenv_path = env_file or ROOT_DIR / ".env"
    load_dotenv(dotenv_path, override=override)

    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        github_copilot_api_key=os.getenv("GITHUB_COPILOT_API_KEY", ""),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        langchain_api_key=os.getenv("LANGCHAIN_API_KEY", ""),
        langchain_tracing_v2=os.getenv("LANGCHAIN_TRACING_V2", "false"),
        langchain_project=os.getenv("LANGCHAIN_PROJECT", DEFAULT_LANGCHAIN_PROJECT),
        agent=AgentRuntimeConfig(
            provider=os.getenv("LLM_PROVIDER", DEFAULT_LLM_PROVIDER),
            model=os.getenv(
                "LLM_MODEL",
                os.getenv("OPENAI_CHAT_MODEL", DEFAULT_LLM_MODEL),
            ),
            temperature=_optional_float("LLM_TEMPERATURE"),
            max_output_tokens=_optional_int("LLM_MAX_OUTPUT_TOKENS"),
            reasoning_effort=os.getenv("LLM_REASONING_EFFORT", "medium"),
            text_verbosity=os.getenv("LLM_TEXT_VERBOSITY", "medium"),
            prompt_cache_retention=os.getenv("OPENAI_PROMPT_CACHE_RETENTION", "auto"),
            memory=MemoryConfig(
                backend=os.getenv("MEMORY_BACKEND", "none"),
                strategy=os.getenv("MEMORY_STRATEGY", "stateless"),
                max_messages=_optional_int("MEMORY_MAX_MESSAGES") or 20,
                max_tokens=_optional_int("MEMORY_MAX_TOKENS"),
                store_provider_state=os.getenv("MEMORY_STORE_PROVIDER_STATE", "false"),
                conversation_id=os.getenv("OPENAI_CONVERSATION_ID", ""),
                previous_response_id=os.getenv("OPENAI_PREVIOUS_RESPONSE_ID", ""),
            ),
        ),
    )


def _optional_int(key: str) -> int | None:
    value = os.getenv(key)
    if value in (None, ""):
        return None
    return int(value)


def _optional_float(key: str) -> float | None:
    value = os.getenv(key)
    if value in (None, ""):
        return None
    return float(value)
