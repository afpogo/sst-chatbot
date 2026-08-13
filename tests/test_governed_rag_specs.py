from __future__ import annotations

from pathlib import Path

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]


def load_yaml(relative_path: str) -> dict:
    return yaml.safe_load((ROOT_DIR / relative_path).read_text(encoding="utf-8"))


def test_governed_rag_owner_spec_and_state_are_linked() -> None:
    capability = load_yaml(
        "specs/capabilities/retrieval-augmented-generation.yaml"
    )
    state = load_yaml("specs/states/sst-user-governed-rag-v1.yaml")
    assert capability["status"] == "active"
    assert capability["local_implementation"]["status"] == "implemented-local"
    assert capability["control_plane_link"] == {
        "repo": "4uentes-orchestor",
        "request_id": "CR-SST-0155",
        "state_id": "sst-user-ards-rag",
        "capability_id": "retrieval-augmented-generation",
        "source_of_truth": False,
    }
    assert state["status"] == "in-progress"
    assert state["control_plane_link"]["status_hint"] == "implemented-local"


def test_capability_contract_requires_authorization_before_ranking() -> None:
    capability = load_yaml(
        "specs/capabilities/retrieval-augmented-generation.yaml"
    )
    rules = " ".join(capability["contract_rules"])
    assert "before ranking" in rules
    assert "no access-granting authority" in rules
    assert "fabricated citations fail closed" in rules
    assert "HTTP, Socket.IO or current chat runtime integration." in capability["non_goals"]


def test_memory_and_connector_specs_preserve_scope_and_read_only_boundary() -> None:
    memory = load_yaml("specs/capabilities/user-activity-ards-memory.yaml")
    connector = load_yaml("specs/capabilities/application-context-connector.yaml")
    projection = memory["rag_read_projection"]
    assert projection["request_id"] == "CR-SST-0155"
    assert any("Raw chats" in rule for rule in projection["rules"])
    retrieval_scope = connector["governed_retrieval_scope"]
    assert set(retrieval_scope["required_fields"]) == {
        "tenant_id",
        "user_id",
        "application_id",
        "entitlements",
        "allowed_classifications",
        "allowed_sources",
        "policy_version",
    }
    assert any("User text cannot" in rule for rule in retrieval_scope["authority_rules"])


def test_governed_rag_capability_evidence_contains_no_business_data() -> None:
    links = load_yaml("specs/integration/capability-links.yaml")
    sync = load_yaml("specs/integrations/sst-chatbot-core-orchestrator-sync.yaml")
    link = next(
        item
        for item in links["capability_links"]
        if item["owner_capability_id"] == "retrieval-augmented-generation"
    )
    evidence = next(
        item
        for item in sync["sync_streams"]["child_capability_evidence"]["capabilities"]
        if item["capability_id"] == "retrieval-augmented-generation"
    )
    assert link["control_plane_parent_capability_id"] == "retrieval-augmented-generation"
    assert link["execution_authority"] == "none"
    assert link["contains_business_data"] is False
    assert evidence["execution_authority"] == "none"
    assert evidence["contains_business_data"] is False
    assert "retrieved_private_chunks" in sync["sync_streams"]["child_capability_evidence"]["forbidden_payloads"]
