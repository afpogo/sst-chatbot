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
    "specs/ards/contract-binding.yaml",
    "specs/integration/policies.yaml",
    "specs/integration/control-plane-link.yaml",
    "specs/policies/00-index.yaml",
    "docs/policies/README.md",
    "docs/ai/policy.md",
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

        if "kind" not in data:
            errors.append(f"{path.relative_to(ROOT_DIR)} missing required key: kind")
        if "version" not in data and "schema_version" not in data:
            errors.append(
                f"{path.relative_to(ROOT_DIR)} missing version or schema_version"
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

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for group_name, entries in grouped_entries.items():
        if not isinstance(entries, list):
            errors.append(f"specs/00-index.yaml entries.{group_name} must be a list")
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                errors.append(f"specs/00-index.yaml entry in {group_name} is invalid")
                continue
            entry_path = entry.get("path")
            entry_id = entry.get("id")
            if entry_id in seen_ids:
                errors.append(f"Duplicate indexed spec id: {entry_id}")
            elif entry_id:
                seen_ids.add(entry_id)
            if entry_path in seen_paths:
                errors.append(f"Duplicate indexed spec path: {entry_path}")
            elif entry_path:
                seen_paths.add(entry_path)
            if not entry_path:
                errors.append(f"specs/00-index.yaml entry in {group_name} missing path")
                continue
            if not (ROOT_DIR / entry_path).exists():
                errors.append(f"Indexed spec does not exist: {entry_path}")
                continue
            artifact = load_yaml(ROOT_DIR / entry_path)
            if artifact.get("id") != entry_id:
                errors.append(f"Indexed spec id mismatch: {entry_path}")
            if artifact.get("status") != entry.get("status"):
                errors.append(f"Indexed spec status mismatch: {entry_path}")
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


def validate_policy_adoption() -> list[str]:
    errors: list[str] = []
    registry_path = ROOT_DIR / "specs" / "integration" / "policies.yaml"
    index_path = ROOT_DIR / "specs" / "policies" / "00-index.yaml"
    binding_path = ROOT_DIR / "specs" / "ards" / "contract-binding.yaml"
    specs_index_path = ROOT_DIR / "specs" / "00-index.yaml"

    registry = load_yaml(registry_path)
    policy_index = load_yaml(index_path)
    binding = load_yaml(binding_path)
    specs_index = load_yaml(specs_index_path)

    repo_ids = {
        registry.get("local_adoption", {}).get("repo"),
        binding.get("repo_id"),
        specs_index.get("repository"),
    }
    if len(repo_ids) != 1:
        rendered_repo_ids = sorted((repr(value) for value in repo_ids))
        errors.append(
            f"Repository id drift across ARDS artifacts: {rendered_repo_ids}"
        )

    aliases = registry.get("provider_model", {}).get("aliases", {})
    required_aliases = registry.get("provider_model", {}).get(
        "required_alias_slots",
        [],
    )
    for alias in required_aliases:
        if not aliases.get(alias):
            errors.append(f"Unresolved required model alias: {alias}")

    registry_policies = registry.get("policies", [])
    indexed_policies = policy_index.get("policies", [])
    registry_ids = {item.get("id") for item in registry_policies}
    indexed_ids = {item.get("id") for item in indexed_policies}
    if len(registry_ids) != len(registry_policies):
        errors.append("Policy registry contains duplicate policy ids")
    if len(indexed_ids) != len(indexed_policies):
        errors.append("Policy index contains duplicate policy ids")
    if registry_ids != indexed_ids:
        errors.append("Policy registry and policy index contain different policy ids")

    adopted_ids = {
        item.get("id")
        for item in registry_policies
        if item.get("adoption_status") == "adopted"
    }
    exception_ids = {
        item.get("id")
        for item in registry_policies
        if item.get("adoption_status") in {"exception", "not-applicable"}
    }
    binding_adopted_ids = set(
        binding.get("core_contract", {}).get("adopted_policy_ids", [])
    )
    binding_exception_ids = set(
        binding.get("core_contract", {}).get("policy_exception_ids", [])
    )
    if adopted_ids != binding_adopted_ids:
        errors.append("Binding and registry contain different adopted policy ids")
    if exception_ids != binding_exception_ids:
        errors.append("Binding and registry contain different policy exception ids")
    if (
        registry.get("standard_source", {}).get("core_ref")
        != binding.get("core_contract", {}).get("core_ref")
    ):
        errors.append("Binding and policy registry core_ref values differ")
    if (
        registry.get("standard_source", {}).get("core_contract_version")
        != binding.get("core_contract", {}).get("resolved_contract_version")
    ):
        errors.append("Binding and policy registry contract versions differ")
    if (
        registry.get("standard_source", {}).get("adoption_mode")
        != binding.get("core_contract", {}).get("adoption_mode")
    ):
        errors.append("Binding and policy registry adoption modes differ")
    if (
        registry.get("standard_source", {}).get("policy_runtime_revision")
        != binding.get("core_contract", {}).get("policy_runtime_revision")
    ):
        errors.append("Binding and policy registry policy runtime revisions differ")

    indexed_by_id = {item.get("id"): item for item in indexed_policies}
    exceptions_by_id = {
        item.get("policy_id"): item for item in registry.get("exceptions", [])
    }

    for policy in registry_policies:
        policy_id = policy.get("id")
        manifest_path = policy.get("manifest")
        if not manifest_path:
            errors.append(f"Policy missing manifest path: {policy_id}")
            continue
        resolved_path = ROOT_DIR / manifest_path
        if not resolved_path.exists():
            errors.append(f"Policy manifest does not exist: {manifest_path}")
            continue
        manifest = load_yaml(resolved_path)
        if manifest.get("policy_id") != policy_id:
            errors.append(f"Policy manifest id mismatch: {manifest_path}")
        expected_kind = (
            "policy_exception_manifest"
            if policy.get("adoption_status") == "exception"
            else "policy_adoption_manifest"
        )
        if manifest.get("kind") != expected_kind:
            errors.append(f"Policy manifest kind mismatch: {policy_id}")
        indexed = indexed_by_id.get(policy_id, {})
        if indexed.get("path") != manifest_path:
            errors.append(f"Policy index path mismatch: {policy_id}")
        manifest_status = (
            manifest.get("exception_status")
            if expected_kind == "policy_exception_manifest"
            else manifest.get("adoption_status")
        )
        expected_index_status = (
            exceptions_by_id.get(policy_id, {}).get("status")
            if expected_kind == "policy_exception_manifest"
            else policy.get("adoption_status")
        )
        if indexed.get("status") != expected_index_status:
            errors.append(f"Policy index status mismatch: {policy_id}")
        if expected_kind == "policy_adoption_manifest" and (
            manifest_status != policy.get("adoption_status")
        ):
            errors.append(f"Policy adoption status mismatch: {policy_id}")
        if expected_kind == "policy_exception_manifest" and (
            manifest_status != expected_index_status
        ):
            errors.append(f"Policy exception status mismatch: {policy_id}")
        if manifest.get("policy_class") != policy.get("policy_class"):
            errors.append(f"Policy class mismatch: {policy_id}")
        if manifest.get("adopting_repo") != "sst-chatbot":
            errors.append(f"Policy adopting repo mismatch: {policy_id}")
        for ref_key in ("local_implementation_path", "validation_ref"):
            local_ref = manifest.get(ref_key)
            if local_ref and not (ROOT_DIR / local_ref).exists():
                errors.append(f"Policy local ref does not exist: {local_ref}")

    if (
        registry.get("local_adoption", {}).get("adoption_completeness", "").startswith(
            "full"
        )
        and registry.get("gaps")
    ):
        errors.append("Full policy adoption cannot declare open gaps")

    return errors


def validate_control_plane_link() -> list[str]:
    errors: list[str] = []
    link = load_yaml(ROOT_DIR / "specs" / "integration" / "control-plane-link.yaml")
    data = link.get("control_plane_link", {})
    if data.get("control_plane_repo") != "4uentes-orchestor":
        errors.append("control_plane_link has an unexpected authority repo")
    if data.get("capability_id") != "capability.inbound.sst-chatbot-agent-handoff":
        errors.append("control_plane_link capability id mismatch")
    if link.get("status") == "active" and "TODO" in str(data.get("request_id", "")):
        errors.append("An active control_plane_link cannot have a TODO request id")
    evidence = data.get("evidence_ref", {})
    if evidence.get("scope") == "local":
        path = evidence.get("path", "")
        if not path or not (ROOT_DIR / path).exists():
            errors.append("control_plane_link local evidence does not exist")
    alias = link.get("alias", {})
    if alias.get("local_key") != "orchestrator_link" or alias.get("maps_to") != "control_plane_link":
        errors.append("control_plane_link local alias is invalid")
    return errors


def main() -> int:
    errors = []
    errors.extend(require_paths())
    errors.extend(validate_yaml_files())
    errors.extend(validate_specs_index())
    errors.extend(validate_notebooks())
    errors.extend(validate_prompt_catalog())
    errors.extend(validate_policy_adoption())
    errors.extend(validate_control_plane_link())

    if errors:
        print("ARDS/SDD check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("ARDS/SDD check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
