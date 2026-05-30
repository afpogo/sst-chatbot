from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    "AGENTS.md",
    "README.md",
    ".env.example",
    "pyproject.toml",
    "docs/00-overview.md",
    "docs/architecture/provider-agnostic-agents.md",
    "docs/architecture/agent-runtime-product-intent.md",
    "docs/adr/0001-adopt-ards-sdd.md",
    "docs/adr/0001-python-agentic-project-structure.md",
    "docs/adr/0002-provider-model-memory-configuration.md",
    "docs/playbooks/01-setup-python-env.md",
    "docs/playbooks/02-run-initial-validation.md",
    "docs/playbooks/03-langsmith-tracing.md",
    "docs/playbooks/04-configure-provider-model-memory.md",
    "docs/playbooks/05-author-and-validate-prompts.md",
    "docs/adr/0003-private-prompt-engine.md",
    "docs/architecture/private-prompt-engine.md",
    "docs/pocs/README.md",
    "docs/tasks/README.md",
    "labs/notebooks",
    "labs/experiments",
    "specs/00-index.yaml",
    "specs/architecture/python-agentic-structure.yaml",
    "specs/architecture/provider-model-memory-configuration.yaml",
    "specs/architecture/agent-runtime-product-intent.yaml",
    "specs/capabilities/prompt-catalog-and-versioning.yaml",
    "specs/capabilities/provider-abstraction.yaml",
    "specs/integrations/sst-agent-feed.yaml",
    "specs/templates/feature.template.yaml",
    "specs/templates/poc.template.yaml",
    "specs/templates/state-scenario.template.yaml",
    "pocs/README.md",
]

REQUIRED_PROMPT_KEYS = (
    "id",
    "version",
    "status",
    "description",
    "messages",
    "variables",
    "visibility",
    "trace_policy",
    "provider_cache_policy",
)


def require_paths() -> list[str]:
    errors: list[str] = []
    for relative_path in REQUIRED_PATHS:
        if not (ROOT_DIR / relative_path).exists():
            errors.append(f"Missing required ARDS/SDD path: {relative_path}")
    return errors


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError("YAML root must be an object")
    return data


def validate_yaml_files() -> list[str]:
    errors: list[str] = []
    for path in sorted((ROOT_DIR / "specs").rglob("*.yaml")):
        try:
            data = load_yaml(path)
        except Exception as exc:
            errors.append(f"Invalid YAML {path.relative_to(ROOT_DIR)}: {exc}")
            continue

        for required_key in ("version", "kind"):
            if required_key not in data:
                errors.append(
                    f"{path.relative_to(ROOT_DIR)} missing required key: {required_key}"
                )
    return errors


def validate_specs_index() -> list[str]:
    errors: list[str] = []
    index_path = ROOT_DIR / "specs" / "00-index.yaml"
    try:
        index = load_yaml(index_path)
    except Exception as exc:
        return [f"Invalid specs/00-index.yaml: {exc}"]

    grouped_entries = index.get("entries", {})
    if not isinstance(grouped_entries, dict):
        return ["specs/00-index.yaml entries must be an object"]

    for group_name, entries in grouped_entries.items():
        if not isinstance(entries, list):
            errors.append(f"specs/00-index.yaml entries.{group_name} must be a list")
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                errors.append(f"specs/00-index.yaml entry in {group_name} is invalid")
                continue
            entry_path = entry.get("path")
            if not entry_path:
                errors.append(f"specs/00-index.yaml entry in {group_name} missing path")
                continue
            if not (ROOT_DIR / entry_path).exists():
                errors.append(f"Indexed spec does not exist: {entry_path}")
    return errors


def validate_notebooks() -> list[str]:
    errors: list[str] = []
    notebooks_dir = ROOT_DIR / "labs" / "notebooks"
    for path in sorted(notebooks_dir.glob("*.ipynb")):
        try:
            with path.open(encoding="utf-8") as file:
                data = json.load(file)
        except Exception as exc:
            errors.append(f"Invalid notebook JSON {path.relative_to(ROOT_DIR)}: {exc}")
            continue

        if data.get("nbformat") is None:
            errors.append(f"{path.relative_to(ROOT_DIR)} missing nbformat")
        if not isinstance(data.get("cells"), list):
            errors.append(f"{path.relative_to(ROOT_DIR)} missing cells list")
    return errors


def validate_prompt_catalog() -> list[str]:
    errors: list[str] = []
    catalog_dir = ROOT_DIR / "src" / "app" / "prompts" / "catalog"
    for path in sorted(catalog_dir.rglob("*.yaml")):
        try:
            data = load_yaml(path)
        except Exception as exc:
            errors.append(f"Invalid prompt YAML {path.relative_to(ROOT_DIR)}: {exc}")
            continue

        for required_key in REQUIRED_PROMPT_KEYS:
            if required_key not in data:
                errors.append(
                    f"{path.relative_to(ROOT_DIR)} missing required key: {required_key}"
                )

        if data.get("trace_policy") != "metadata_only":
            errors.append(
                f"{path.relative_to(ROOT_DIR)} trace_policy must be metadata_only"
            )
        if data.get("visibility") != "internal_private":
            errors.append(
                f"{path.relative_to(ROOT_DIR)} visibility must be internal_private"
            )
        if data.get("provider_cache_policy") not in {"none", "in_memory", "24h"}:
            errors.append(
                f"{path.relative_to(ROOT_DIR)} provider_cache_policy is invalid"
            )

        messages = data.get("messages")
        if not isinstance(messages, list) or not messages:
            errors.append(f"{path.relative_to(ROOT_DIR)} messages must be a non-empty list")
            continue

        for index, message in enumerate(messages):
            if not isinstance(message, dict):
                errors.append(
                    f"{path.relative_to(ROOT_DIR)} messages[{index}] must be an object"
                )
                continue
            if message.get("role") not in {"system", "human", "assistant"}:
                errors.append(
                    f"{path.relative_to(ROOT_DIR)} messages[{index}] has invalid role"
                )
            if not isinstance(message.get("template"), str) or not message.get("template"):
                errors.append(
                    f"{path.relative_to(ROOT_DIR)} messages[{index}] missing template"
                )

    return errors


def main() -> int:
    errors = []
    errors.extend(require_paths())
    errors.extend(validate_yaml_files())
    errors.extend(validate_specs_index())
    errors.extend(validate_notebooks())
    errors.extend(validate_prompt_catalog())

    if errors:
        print("ARDS/SDD check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("ARDS/SDD check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
