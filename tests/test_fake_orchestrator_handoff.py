from __future__ import annotations

import pytest

from app.memory import AuditMetadata
from app.memory import OperationalRecord
from app.memory import stable_body_hash
from app.memory import to_handoff_payload
from app.orchestrator import FakeOrchestratorClient
from app.orchestrator import ReviewEvidence


def make_payload(
    *,
    operation: str = "workspace.generate_bundle",
    idempotency_key: str = "idem-1",
) -> dict[str, object]:
    record = OperationalRecord(
        id="intent-1",
        record_type="intent",
        tenant_id="tenant-1",
        user_id="user-1",
        correlation_id="corr-1",
        idempotency_key=idempotency_key,
        producer="test",
        capability_id="capability.inbound.sst-chatbot-agent-handoff",
        tags=("domain:sst", "kind:intent"),
        provenance={"was_attributed_to": "pytest"},
        body={"summary": operation},
        body_hash=stable_body_hash({"summary": operation}),
        audit_metadata=AuditMetadata(
            origin_service="sst-chatbot",
            created_by="pytest",
            reason="unit test",
        ),
        payload={
            "requested_operation": operation,
            "priority": "normal",
            "requested_retry_policy": "none",
        },
    )
    return to_handoff_payload(record)


def test_valid_payload_returns_accepted_for_review_receipt() -> None:
    client = FakeOrchestratorClient()

    receipt = client.submit(make_payload())

    assert receipt.status == "accepted_for_review"
    assert receipt.decision.accepted is True
    assert receipt.correlation_id == "corr-1"
    assert receipt.audit_metadata["origin_service"] == "sst-chatbot"


def test_missing_correlation_or_idempotency_is_rejected() -> None:
    payload = make_payload()
    payload["correlation_id"] = ""
    payload["idempotency_key"] = ""

    receipt = FakeOrchestratorClient().submit(payload)

    assert receipt.status == "rejected_by_policy"
    assert receipt.decision.accepted is False
    assert {issue.code for issue in receipt.decision.issues} == {
        "missing_required_field"
    }


def test_duplicate_idempotency_with_same_payload_returns_duplicate() -> None:
    client = FakeOrchestratorClient()
    payload = make_payload(idempotency_key="idem-dup")

    first = client.submit(payload)
    second = client.submit(payload)

    assert first.status == "accepted_for_review"
    assert second.status == "duplicate"
    assert second.receipt_id == first.receipt_id


def test_same_idempotency_with_different_payload_returns_conflict() -> None:
    client = FakeOrchestratorClient()
    first = make_payload(idempotency_key="idem-conflict")
    second = make_payload(
        operation="user_history.propose_update",
        idempotency_key="idem-conflict",
    )

    client.submit(first)
    receipt = client.submit(second)

    assert receipt.status == "conflict"
    assert receipt.decision.accepted is False
    assert receipt.decision.issues[0].code == "idempotency_conflict"


def test_server_operations_are_rejected_before_fake_client_acceptance() -> None:
    with pytest.raises(ValueError, match="server.restart_service is blocked"):
        make_payload(operation="server.restart_service")


def test_workspace_apply_patch_requires_human_review() -> None:
    client = FakeOrchestratorClient()
    payload = make_payload(operation="workspace.apply_patch")

    rejected = client.submit(payload)
    accepted = client.submit(
        payload,
        review_evidence=ReviewEvidence(
            reviewer="pytest",
            reason="approved test patch",
            evidence_ref="review-1",
        ),
    )

    assert rejected.status == "rejected_by_policy"
    assert "human_review_required" in {
        issue.code for issue in rejected.decision.issues
    }
    assert accepted.status == "accepted_for_review"


@pytest.mark.parametrize("operation", ["", "totally.unknown"])
def test_missing_or_unknown_operations_are_rejected(operation: str) -> None:
    payload = make_payload()
    payload["payload"]["requested_operation"] = operation

    receipt = FakeOrchestratorClient().submit(payload)

    assert receipt.status == "rejected_by_policy"
    assert receipt.decision.accepted is False
    assert receipt.decision.issues[0].code in {
        "missing_requested_operation",
        "unsupported_operation",
    }
