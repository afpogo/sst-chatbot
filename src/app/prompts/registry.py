from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.prompts.types import PromptDefinition
from app.prompts.validators import validate_prompt_definition

PROMPTS_DIR = Path(__file__).resolve().parent

CATALOG_PATHS = {
    "task.article_final_stage": PROMPTS_DIR / "catalog" / "tasks" / "article_final_stage.yaml",
    "task.article_analysis": PROMPTS_DIR / "catalog" / "tasks" / "article_analysis.yaml",
    "system.sst_base_assistant": PROMPTS_DIR
    / "catalog"
    / "system"
    / "sst_base_assistant.yaml",
    "agent.creator": PROMPTS_DIR / "catalog" / "agents" / "agent_creator.yaml",
    "task.classify_request": PROMPTS_DIR
    / "catalog"
    / "tasks"
    / "classify_request.yaml",
}


def get_prompt_definition(prompt_id: str, version: str | None = None) -> PromptDefinition:
    matches = [
        prompt
        for prompt in list_prompt_definitions()
        if prompt.id == prompt_id and (version is None or prompt.version == version)
    ]
    if not matches:
        version_label = version if version is not None else "any"
        raise KeyError(f"Prompt not found: {prompt_id}:{version_label}")
    if len(matches) > 1:
        raise ValueError(f"Prompt version must be explicit for duplicate id: {prompt_id}")
    return matches[0]


@lru_cache(maxsize=1)
def list_prompt_definitions() -> tuple[PromptDefinition, ...]:
    prompts = tuple(
        _load_prompt(prompt_id, path) for prompt_id, path in CATALOG_PATHS.items()
    )
    _validate_unique_prompt_keys(prompts)
    return prompts


def _load_prompt(expected_prompt_id: str, path: Path) -> PromptDefinition:
    resolved_path = path.resolve()
    if not resolved_path.is_relative_to(PROMPTS_DIR):
        raise ValueError(f"Prompt path must stay under {PROMPTS_DIR}: {path}")

    with resolved_path.open(encoding="utf-8") as file:
        data: Any = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Prompt YAML root must be an object: {path}")

    prompt = PromptDefinition(**data)
    if prompt.id != expected_prompt_id:
        raise ValueError(
            f"Prompt id mismatch for {path}: expected {expected_prompt_id}, got {prompt.id}"
        )
    validate_prompt_definition(prompt)
    return prompt


def _validate_unique_prompt_keys(prompts: tuple[PromptDefinition, ...]) -> None:
    seen: set[tuple[str, str]] = set()
    for prompt in prompts:
        key = (prompt.id, prompt.version)
        if key in seen:
            raise ValueError(f"Duplicate prompt id/version: {prompt.id}:{prompt.version}")
        seen.add(key)
