from __future__ import annotations

from hashlib import sha256
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
    "docs/architecture/audience-safe-disclosure.md",
    "docs/architecture/control-plane-capability-links.md",
    "docs/adr/0001-adopt-ards-sdd.md",
    "docs/adr/0001-python-agentic-project-structure.md",
    "docs/adr/0002-provider-model-memory-configuration.md",
    "docs/playbooks/01-setup-python-env.md",
    "docs/playbooks/02-run-initial-validation.md",
    "docs/playbooks/03-langsmith-tracing.md",
    "docs/playbooks/04-configure-provider-model-memory.md",
    "docs/playbooks/05-author-and-validate-prompts.md",
    "docs/adr/0003-private-prompt-engine.md",
    "docs/adr/0004-audience-safe-disclosure.md",
    "docs/architecture/private-prompt-engine.md",
    "docs/pocs/README.md",
    "docs/tasks/README.md",
    "labs/notebooks",
    "labs/experiments",
    "specs/00-index.yaml",
    "specs/architecture/python-agentic-structure.yaml",
    "specs/architecture/provider-model-memory-configuration.yaml",
    "specs/architecture/agent-runtime-product-intent.yaml",
    "specs/architecture/audience-safe-disclosure.yaml",
    "specs/ards/contract-binding.yaml",
    "specs/integration/policies.yaml",
    "specs/integration/control-plane-link.yaml",
    "specs/integration/capability-links.yaml",
    "specs/policies/00-index.yaml",
    "docs/policies/README.md",
    "docs/ai/policy.md",
    "specs/capabilities/prompt-catalog-and-versioning.yaml",
    "specs/capabilities/provider-abstraction.yaml",
    "specs/capabilities/audience-aware-context-governance.yaml",
    "specs/capabilities/sst-user-assistant.yaml",
    "specs/capabilities/sst-stakeholder-insights.yaml",
    "specs/integrations/sst-agent-feed.yaml",
    "specs/states/sst-chatbot-audience-access-v1.yaml",
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


def capability_movement_digest(owner_ref: str, evidence_ref: str) -> str:
    owner = load_yaml(ROOT_DIR / owner_ref)
    local_implementation = owner.get("local_implementation", {})
    refs = {owner_ref, evidence_ref}
    refs.update(local_implementation.get("code", []))
    refs.update(local_implementation.get("tests", []))
    digest = sha256()
    for ref in sorted(refs):
        digest.update(ref.encode("utf-8"))
        digest.update(b"\0")
        digest.update((ROOT_DIR / ref).read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


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
    if link.get("status") != "active":
        errors.append("control_plane_link must be active")
    if link.get("status") == "active" and "TODO" in str(data.get("request_id", "")):
        errors.append("An active control_plane_link cannot have a TODO request id")
    evidence = data.get("evidence_ref", {})
    if evidence.get("scope") == "local":
        path = evidence.get("path", "")
        if not path or not (ROOT_DIR / path).exists():
            errors.append("control_plane_link local evidence does not exist")
    child_evidence = data.get("child_capability_evidence_ref", {})
    if child_evidence.get("scope") != "local":
        errors.append("control_plane_link child capability evidence must be local")
    child_evidence_path = child_evidence.get("path", "")
    if not child_evidence_path or not (ROOT_DIR / child_evidence_path).exists():
        errors.append("control_plane_link child capability evidence does not exist")
    capability_links = data.get("capability_links_ref", {})
    if capability_links.get("scope") != "local":
        errors.append("control_plane_link capability links must be local owner evidence")
    capability_links_path = capability_links.get("path", "")
    if not capability_links_path or not (ROOT_DIR / capability_links_path).exists():
        errors.append("control_plane_link capability links do not exist")
    alias = link.get("alias", {})
    if alias.get("local_key") != "orchestrator_link" or alias.get("maps_to") != "control_plane_link":
        errors.append("control_plane_link local alias is invalid")
    pending = link.get("pending_capability_reconciliation", {})
    if pending.get("request_id") != "CR-SST-0155":
        errors.append("Pending capability reconciliation must reference CR-SST-0155")
    if pending.get("status") != "in-progress-owner-evidence-ready":
        errors.append("Pending capability reconciliation status is stale")
    pending_ref = pending.get("evidence_ref", "")
    if not pending_ref or not (ROOT_DIR / pending_ref).exists():
        errors.append("Pending capability reconciliation evidence does not exist")
    return errors


def validate_capability_links() -> list[str]:
    errors: list[str] = []
    registry = load_yaml(ROOT_DIR / "specs" / "integration" / "capability-links.yaml")
    expected_capability_ids = {
        "audience-aware-context-governance",
        "retrieval-augmented-generation",
        "sst-user-assistant",
        "sst-stakeholder-insights",
    }
    expected_parent_id = "capability.inbound.sst-chatbot-agent-handoff"
    expected_parents = {
        capability_id: (
            "retrieval-augmented-generation"
            if capability_id == "retrieval-augmented-generation"
            else expected_parent_id
        )
        for capability_id in expected_capability_ids
    }
    if registry.get("status") != "active":
        errors.append("Audience capability link registry must be active")
    control_plane = registry.get("control_plane", {})
    if control_plane.get("repo") != "4uentes-orchestor":
        errors.append("Capability link registry has an unexpected control-plane repo")
    if control_plane.get("parent_capability_id") != expected_parent_id:
        errors.append("Capability link registry parent capability mismatch")
    activation = registry.get("activation", {})
    if activation.get("status") != "active":
        errors.append("Capability link registry activation must be active")
    if activation.get("established_by_request") != "CR-SST-0082":
        errors.append("Capability link registry must use the known establishment request")
    pending = activation.get("capability_reconciliation", {})
    if pending.get("request_id") != "CR-SST-0155":
        errors.append("Capability reconciliation must reference CR-SST-0155")
    if pending.get("status") != "local-owner-evidence-ready":
        errors.append("Capability reconciliation status is stale")

    delivery = registry.get("delivery", {})
    if delivery.get("mode") != "owner-manifest-pull":
        errors.append("Capability links must use the approved owner manifest pull mode")
    if delivery.get("checked_on_every_repository_gate") is not True:
        errors.append("Capability links must be checked on every repository gate")
    if delivery.get("automatic_remote_push") is not False:
        errors.append("Capability links cannot claim an unimplemented remote push")
    if not delivery.get("remote_push_blocker"):
        errors.append("Capability links must document the remote push blocker")

    links = registry.get("capability_links", [])
    links_by_capability = {item.get("owner_capability_id"): item for item in links}
    if set(links_by_capability) != expected_capability_ids or len(links) != len(
        expected_capability_ids
    ):
        errors.append("Audience capability link inventory is incomplete or duplicated")

    sync = load_yaml(
        ROOT_DIR / "specs" / "integrations" / "sst-chatbot-core-orchestrator-sync.yaml"
    )
    stream = sync.get("sync_streams", {}).get("child_capability_evidence", {})
    stream_by_capability = {
        item.get("capability_id"): item for item in stream.get("capabilities", [])
    }
    if stream.get("status") != "active":
        errors.append("Child capability evidence stream must be active")
    if stream.get("capability_links_ref") != "specs/integration/capability-links.yaml":
        errors.append("Child capability evidence stream link reference mismatch")

    for capability_id in expected_capability_ids:
        link = links_by_capability.get(capability_id, {})
        owner_ref = link.get("owner_spec_ref", "")
        if not owner_ref or not (ROOT_DIR / owner_ref).exists():
            errors.append(f"Capability link owner spec does not exist: {capability_id}")
            continue
        owner = load_yaml(ROOT_DIR / owner_ref)
        if owner.get("id") != capability_id:
            errors.append(f"Capability link owner id mismatch: {capability_id}")
        if owner.get("status") != link.get("owner_status"):
            errors.append(f"Capability link owner status drift: {capability_id}")
        if link.get("owner_status") != "active":
            errors.append(f"Linked audience capability must be active: {capability_id}")
        if link.get("control_plane_parent_capability_id") != expected_parents[capability_id]:
            errors.append(f"Capability link parent mismatch: {capability_id}")
        if link.get("execution_authority") != "none":
            errors.append(f"Capability link has execution authority: {capability_id}")
        if link.get("contains_business_data") is not False:
            errors.append(f"Capability link contains business data: {capability_id}")
        evidence_ref = link.get("evidence_ref", "")
        if not evidence_ref or not (ROOT_DIR / evidence_ref).exists():
            errors.append(f"Capability link evidence does not exist: {capability_id}")
        elif link.get("movement_digest") != capability_movement_digest(
            owner_ref,
            evidence_ref,
        ):
            errors.append(f"Capability link movement digest is stale: {capability_id}")
        stream_item = stream_by_capability.get(capability_id, {})
        if stream_item.get("capability_status") != link.get("owner_status"):
            errors.append(f"Capability evidence stream status drift: {capability_id}")
        if stream_item.get("movement_digest") != link.get("movement_digest"):
            errors.append(f"Capability evidence stream digest drift: {capability_id}")

    return errors


def validate_audience_access() -> list[str]:
    errors: list[str] = []
    capability_ids = {
        "audience-aware-context-governance",
        "sst-user-assistant",
        "sst-stakeholder-insights",
    }
    capability_paths = {
        capability_id: ROOT_DIR / "specs" / "capabilities" / f"{capability_id}.yaml"
        for capability_id in capability_ids
    }
    capabilities = {
        capability_id: load_yaml(path)
        for capability_id, path in capability_paths.items()
    }
    specs_index = load_yaml(ROOT_DIR / "specs" / "00-index.yaml")
    indexed_capabilities = {
        item.get("id"): item
        for item in specs_index.get("entries", {}).get("capabilities", [])
    }
    for capability_id, capability in capabilities.items():
        if capability.get("status") != "active":
            errors.append(f"Audience capability must be active: {capability_id}")
        indexed = indexed_capabilities.get(capability_id, {})
        if indexed.get("status") != "active":
            errors.append(f"Audience capability index status mismatch: {capability_id}")
        local = capability.get("local_implementation", {})
        if local.get("status") != "implemented-local":
            errors.append(f"Missing local implementation evidence: {capability_id}")
        for evidence_group in ("code", "tests"):
            for evidence_ref in local.get(evidence_group, []):
                if not (ROOT_DIR / evidence_ref).exists():
                    errors.append(f"Audience capability evidence does not exist: {evidence_ref}")

    governance = capabilities["audience-aware-context-governance"]
    expected_matrix = {
        ("sst_user", "sst_backend"): {"public", "internal", "private"},
        ("sst_stakeholder", "approved_analytics"): {"public", "derived_safe"},
    }
    actual_matrix: dict[tuple[str, str], set[str]] = {}
    for row in governance.get("access_matrix", []):
        key = (row.get("audience"), row.get("source"))
        if key in actual_matrix:
            errors.append(f"Duplicate audience access matrix row: {key}")
        actual_matrix[key] = set(row.get("allowed_classifications", []))
    if actual_matrix != expected_matrix:
        errors.append("Audience classification and source matrix is not the V1 contract")
    if governance.get("deny_by_default") is not True:
        errors.append("Audience access policy must deny by default")
    if set(governance.get("absolute_denials", [])) != {"restricted", "secret"}:
        errors.append("restricted and secret must be absolute denials")

    stakeholder = capabilities["sst-stakeholder-insights"]
    expected_metrics = {
        "active_accounts",
        "active_users",
        "new_accounts",
        "retention_rate",
        "operation_volume",
        "module_adoption",
    }
    catalog = stakeholder.get("metric_catalog", [])
    if set(catalog) != expected_metrics or len(catalog) != len(expected_metrics):
        errors.append("Stakeholder metric catalog must contain the six unique V1 KPIs")
    if stakeholder.get("granularity") != "monthly":
        errors.append("Stakeholder metric granularity must be monthly")
    if stakeholder.get("minimum_cohort_size") != 10:
        errors.append("Stakeholder minimum cohort size must be 10")
    if stakeholder.get("dimensions") != {"module_adoption": ["module_id"]}:
        errors.append("module_id must be the only initial stakeholder dimension")
    for forbidden_flag in (
        "free_filters_allowed",
        "tenant_drill_down_allowed",
        "raw_records_allowed",
    ):
        if stakeholder.get(forbidden_flag) is not False:
            errors.append(f"Stakeholder policy flag must be false: {forbidden_flag}")

    state_path = ROOT_DIR / "specs" / "states" / "sst-chatbot-audience-access-v1.yaml"
    state = load_yaml(state_path)
    state_index = load_yaml(ROOT_DIR / "specs" / "states" / "00-index.yaml")
    indexed_states = {item.get("id"): item for item in state_index.get("states", [])}
    if state.get("status") != "in-progress":
        errors.append("Audience feature state must be in-progress")
    if indexed_states.get(state.get("id"), {}).get("status") != state.get("status"):
        errors.append("Audience feature state index status mismatch")
    evidence = state.get("evidence", {})
    for evidence_group in ("code", "tests"):
        for evidence_ref in evidence.get(evidence_group, []):
            if not (ROOT_DIR / evidence_ref).exists():
                errors.append(f"Audience feature evidence does not exist: {evidence_ref}")
    tests_source = "\n".join(
        (ROOT_DIR / evidence_ref).read_text(encoding="utf-8")
        for evidence_ref in evidence.get("tests", [])
    )
    for test_case in evidence.get("test_cases", []):
        if f"def {test_case}(" not in tests_source:
            errors.append(f"Audience feature test evidence is stale: {test_case}")

    sync = load_yaml(
        ROOT_DIR / "specs" / "integrations" / "sst-chatbot-core-orchestrator-sync.yaml"
    )
    child_stream = sync.get("sync_streams", {}).get("child_capability_evidence", {})
    child_evidence = child_stream.get("capabilities", [])
    child_by_id = {item.get("capability_id"): item for item in child_evidence}
    if not capability_ids.issubset(set(child_by_id)) or len(child_by_id) != len(child_evidence):
        errors.append("Control-plane child capability inventory is incomplete or duplicated")
    for capability_id in capability_ids:
        item = child_by_id.get(capability_id, {})
        if item.get("owner") != "sst-chatbot":
            errors.append(f"Child capability owner mismatch: {capability_id}")
        if item.get("local_status") != "implemented-local":
            errors.append(f"Child capability local status mismatch: {capability_id}")
        if item.get("execution_authority") != "none":
            errors.append(f"Child capability must have no execution authority: {capability_id}")
        if item.get("contains_business_data") is not False:
            errors.append(f"Child capability evidence contains business data: {capability_id}")
        for evidence_ref in item.get("evidence", []):
            if not (ROOT_DIR / evidence_ref).exists():
                errors.append(f"Child capability evidence does not exist: {evidence_ref}")

    return errors


def validate_governed_rag() -> list[str]:
    errors: list[str] = []
    capability_path = ROOT_DIR / "specs/capabilities/retrieval-augmented-generation.yaml"
    capability = load_yaml(capability_path)
    if capability.get("status") != "active":
        errors.append("Governed RAG capability must be active")
    local = capability.get("local_implementation", {})
    if local.get("status") != "implemented-local":
        errors.append("Governed RAG local implementation evidence is missing")
    for group in ("code", "tests"):
        for evidence_ref in local.get(group, []):
            if not (ROOT_DIR / evidence_ref).exists():
                errors.append(f"Governed RAG evidence does not exist: {evidence_ref}")
    for key in ("smoke", "state_ref", "owner_doc_ref"):
        evidence_ref = local.get(key, "")
        if not evidence_ref or not (ROOT_DIR / evidence_ref).exists():
            errors.append(f"Governed RAG local ref does not exist: {key}={evidence_ref}")

    state_path = ROOT_DIR / "specs/states/sst-user-governed-rag-v1.yaml"
    state = load_yaml(state_path)
    state_index = load_yaml(ROOT_DIR / "specs/states/00-index.yaml")
    indexed = {item.get("id"): item for item in state_index.get("states", [])}
    if state.get("status") != "in-progress":
        errors.append("Governed RAG state must remain in-progress until integration")
    if indexed.get(state.get("id"), {}).get("status") != state.get("status"):
        errors.append("Governed RAG state index status mismatch")
    evidence = state.get("evidence", {})
    refs: list[str] = []
    for group in ("code", "tests", "smoke", "owner_docs"):
        refs.extend(evidence.get(group, []))
    for evidence_ref in refs:
        if not (ROOT_DIR / evidence_ref).exists():
            errors.append(f"Governed RAG state evidence does not exist: {evidence_ref}")
    tests_source = "\n".join(
        (ROOT_DIR / evidence_ref).read_text(encoding="utf-8")
        for evidence_ref in evidence.get("tests", [])
    )
    for test_case in evidence.get("test_cases", []):
        if f"def {test_case}(" not in tests_source:
            errors.append(f"Governed RAG test evidence is stale: {test_case}")
    if "scripts/smoke_governed_rag.py" not in (
        ROOT_DIR / "scripts/check.py"
    ).read_text(encoding="utf-8"):
        errors.append("Repository check does not execute the governed RAG smoke")
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
    errors.extend(validate_capability_links())
    errors.extend(validate_audience_access())
    errors.extend(validate_governed_rag())

    if errors:
        print("ARDS/SDD check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("ARDS/SDD check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
