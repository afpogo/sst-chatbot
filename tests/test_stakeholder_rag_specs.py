from __future__ import annotations

from pathlib import Path

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]


def load_yaml(relative_path: str) -> dict:
    return yaml.safe_load((ROOT_DIR / relative_path).read_text(encoding="utf-8"))


def test_stakeholder_rag_owner_spec_and_state_are_linked() -> None:
    capability = load_yaml("specs/capabilities/sst-stakeholder-insights.yaml")
    state = load_yaml("specs/states/sst-stakeholder-metrics-rag-v1.yaml")
    assert capability["status"] == "active"
    assert capability["local_implementation"]["status"] == "implemented-local"
    assert capability["control_plane_link"]["request_id"] == "CR-SST-0156"
    assert capability["control_plane_link"]["state_id"] == "sst-stakeholder-metrics-rag"
    assert state["status"] == "in-progress"
    assert state["control_plane_link"]["status_hint"] == "implemented-local"


def test_stakeholder_rag_keeps_analytics_and_methodology_authorities_separate() -> None:
    capability = load_yaml("specs/capabilities/sst-stakeholder-insights.yaml")
    assert capability["approved_sources"] == {
        "metric_values": "approved_analytics",
        "documentary_context": "approved_methodology",
    }
    assert capability["methodology_retrieval"]["authorization_before_ranking"] is True
    assert capability["methodology_retrieval"]["can_calculate_metric_values"] is False
    assert capability["output_contract"]["exact_snapshot_claims_required"] is True
    assert capability["output_contract"]["retrieved_citations_required"] is True
    assert capability["output_contract"]["numeric_narrative_allowed"] is False


def test_stakeholder_rag_evidence_contains_no_business_data() -> None:
    links = load_yaml("specs/integration/capability-links.yaml")
    sync = load_yaml("specs/integrations/sst-chatbot-core-orchestrator-sync.yaml")
    link = next(
        item
        for item in links["capability_links"]
        if item["owner_capability_id"] == "sst-stakeholder-insights"
    )
    evidence = next(
        item
        for item in sync["sync_streams"]["child_capability_evidence"]["capabilities"]
        if item["capability_id"] == "sst-stakeholder-insights"
    )
    assert link["evidence_ref"] == "specs/states/sst-stakeholder-metrics-rag-v1.yaml"
    assert link["execution_authority"] == "none"
    assert link["contains_business_data"] is False
    assert evidence["execution_authority"] == "none"
    assert evidence["contains_business_data"] is False
    forbidden = sync["sync_streams"]["child_capability_evidence"]["forbidden_payloads"]
    assert "metric_values" in forbidden
    assert "grounded_answer_content" in forbidden
