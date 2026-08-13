from __future__ import annotations

from pathlib import Path

import yaml

from app.audience_access.contracts import MetricId
from app.audience_access.policy import MINIMUM_COHORT_SIZE


ROOT_DIR = Path(__file__).resolve().parents[1]


def load_yaml(relative_path: str) -> dict:
    return yaml.safe_load((ROOT_DIR / relative_path).read_text(encoding="utf-8"))


def test_runtime_metric_catalog_matches_the_owner_capability() -> None:
    capability = load_yaml("specs/capabilities/sst-stakeholder-insights.yaml")
    assert {item.value for item in MetricId} == set(capability["metric_catalog"])
    assert len(capability["metric_catalog"]) == len(MetricId)
    assert capability["granularity"] == "monthly"
    assert capability["minimum_cohort_size"] == MINIMUM_COHORT_SIZE == 10
    assert capability["dimensions"] == {"module_adoption": ["module_id"]}


def test_audience_capabilities_are_active_with_local_evidence_separated() -> None:
    capability_ids = (
        "audience-aware-context-governance",
        "sst-user-assistant",
        "sst-stakeholder-insights",
    )
    index = load_yaml("specs/00-index.yaml")
    indexed = {
        entry["id"]: entry
        for entry in index["entries"]["capabilities"]
        if entry["id"] in capability_ids
    }
    assert set(indexed) == set(capability_ids)
    for capability_id in capability_ids:
        capability = load_yaml(f"specs/capabilities/{capability_id}.yaml")
        assert capability["status"] == indexed[capability_id]["status"] == "active"
        assert capability["local_implementation"]["status"] == "implemented-local"


def test_control_plane_capability_inventory_contains_technical_evidence_only() -> None:
    sync = load_yaml(
        "specs/integrations/sst-chatbot-core-orchestrator-sync.yaml"
    )
    stream = sync["sync_streams"]["child_capability_evidence"]
    assert sync["status"] == "active"
    assert stream["status"] == "active"
    assert stream["capability_links_ref"] == "specs/integration/capability-links.yaml"
    assert stream["payload_class"] == "technical_maturity_only"
    assert set(stream["forbidden_payloads"]) == {
        "grounded_answer_content",
        "user_queries",
        "assistant_responses",
        "metric_values",
        "retrieved_private_chunks",
        "tenant_or_person_identifiers",
    }
    expected_ids = {
        "audience-aware-context-governance",
        "retrieval-augmented-generation",
        "sst-user-assistant",
        "sst-stakeholder-insights",
    }
    inventory = stream["capabilities"]
    assert {item["capability_id"] for item in inventory} == expected_ids
    assert len(inventory) == len(expected_ids)
    for item in inventory:
        assert item["owner"] == "sst-chatbot"
        assert item["capability_status"] == "active"
        assert item["local_status"] == "implemented-local"
        assert item["execution_authority"] == "none"
        assert item["contains_business_data"] is False
        assert item["evidence"]
        assert all((ROOT_DIR / ref).exists() for ref in item["evidence"])


def test_control_plane_link_is_active_without_inventing_a_new_reconciliation() -> None:
    link = load_yaml("specs/integration/control-plane-link.yaml")
    assert link["status"] == "active"
    assert link["control_plane_link"]["request_id"] == "CR-SST-0082"
    assert "receipt" not in link["control_plane_link"]
    pending = link["pending_capability_reconciliation"]
    assert pending["request_id"] == "CR-SST-0155"
    assert pending["status"] == "in-progress-owner-evidence-ready"
    assert (ROOT_DIR / pending["evidence_ref"]).exists()
    child_ref = link["control_plane_link"]["child_capability_evidence_ref"]
    assert child_ref["scope"] == "local"
    assert (ROOT_DIR / child_ref["path"]).exists()


def test_capability_links_track_owner_status_and_safe_evidence() -> None:
    registry = load_yaml("specs/integration/capability-links.yaml")
    assert registry["status"] == "active"
    assert registry["delivery"]["checked_on_every_repository_gate"] is True
    assert registry["delivery"]["automatic_remote_push"] is False
    assert registry["change_contract"]["contains_business_data"] is False
    for link in registry["capability_links"]:
        owner = load_yaml(link["owner_spec_ref"])
        assert owner["id"] == link["owner_capability_id"]
        assert owner["status"] == link["owner_status"] == "active"
        assert link["execution_authority"] == "none"
        assert link["contains_business_data"] is False
        assert link["movement_digest"].startswith("sha256:")
        assert len(link["movement_digest"]) == 71
        assert (ROOT_DIR / link["evidence_ref"]).exists()
