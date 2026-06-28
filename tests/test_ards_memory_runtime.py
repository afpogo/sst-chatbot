from __future__ import annotations

import pytest

from app.memory import AuditMetadata
from app.memory import FakeAgentProvider
from app.memory import InMemoryRecordStore
from app.memory import OperationalRecord
from app.memory import PhaseRunner
from app.memory import build_visibility_candidates
from app.memory import stable_body_hash
from app.memory import to_agent_result
from app.memory import to_handoff_payload
from app.memory.validation import validate_record


def make_record(
    record_id: str = "intent-1",
    record_type: str = "intent",
    status: str = "pending",
) -> OperationalRecord:
    return OperationalRecord(
        id=record_id,
        record_type=record_type,
        tenant_id="tenant-1",
        user_id="user-1",
        correlation_id="corr-1",
        idempotency_key=f"idem-{record_id}",
        producer="test",
        capability_id="capability.inbound.sst-chatbot-agent-handoff",
        status=status,
        tags=("domain:sst", "kind:intent"),
        provenance={"was_attributed_to": "pytest"},
        body={"summary": record_id},
        body_hash=stable_body_hash({"summary": record_id}),
        audit_metadata=AuditMetadata(
            origin_service="sst-chatbot",
            created_by="pytest",
            reason="unit test",
        ),
        payload={"priority": "normal", "requested_retry_policy": "none"},
    )


def test_operational_record_requires_scope_correlation_idempotency_and_audit() -> None:
    record = OperationalRecord(
        id="bad-1",
        record_type="intent",
        correlation_id="",
        idempotency_key="",
        producer="",
        audit_metadata=AuditMetadata(
            origin_service="",
            created_by="",
            reason="",
        ),
    )

    result = validate_record(record)

    assert result.accepted is False
    assert {issue.code for issue in result.issues} == {
        "missing_required_field",
        "missing_scope",
    }


def test_in_memory_store_indexes_correlation_and_handles_idempotency() -> None:
    store = InMemoryRecordStore()
    first = make_record("intent-1")
    same_operation = make_record("intent-2").model_copy(
        update={
            "idempotency_key": first.idempotency_key,
            "payload": first.payload,
            "body": first.body,
            "body_hash": first.body_hash,
        }
    )
    conflicting = make_record("intent-3").model_copy(
        update={
            "idempotency_key": first.idempotency_key,
            "payload": {"priority": "urgent"},
        }
    )

    store.append(first)

    assert store.get("intent-1") == first
    assert store.find_by_correlation("corr-1") == (first,)
    assert store.find_by_idempotency(first.idempotency_key) == first
    assert store.append(same_operation) == first
    with pytest.raises(ValueError, match="idempotency_key conflict"):
        store.append(conflicting)


def test_phase_runner_emits_phase_run_and_fake_agent_execution() -> None:
    store = InMemoryRecordStore()
    intent = make_record("intent-1")
    store.append(intent)
    runner = PhaseRunner(store, provider=FakeAgentProvider())

    result = runner.run("run_provider_adapter", (intent,))

    assert result.validation.accepted is True
    assert [record.record_type for record in result.emitted_records] == [
        "phase_run",
        "agent_execution",
    ]
    assert store.find_by_idempotency("phase:run_provider_adapter:intent-1") is not None
    assert to_agent_result(result.emitted_records[1])["operation_intent_id"] == "intent-1"


def test_prepare_handoff_phase_requires_explicit_human_review() -> None:
    store = InMemoryRecordStore()
    intent = make_record("intent-1")
    store.append(intent)
    runner = PhaseRunner(store)

    result = runner.run("prepare_handoff", (intent,))

    assert result.validation.accepted is False
    assert result.phase_run.status == "rejected"
    assert result.validation.issues[0].code == "human_review_required"


def test_visibility_candidates_are_created_for_pending_memory_items() -> None:
    decision = make_record("decision-1", "decision", "accepted")
    reminder = make_record("reminder-1", "reminder", "pending")
    runtime_event = make_record("event-1", "runtime_event", "completed")

    candidates = build_visibility_candidates((decision, reminder, runtime_event))

    assert [candidate.source_record_ids for candidate in candidates] == [
        ("decision-1",),
        ("reminder-1",),
    ]
    assert all(candidate.record_type == "visibility_candidate" for candidate in candidates)


def test_handoff_payload_matches_orchestrator_required_fields() -> None:
    intent = make_record("intent-1")

    payload = to_handoff_payload(intent)

    assert payload["operation_intent_id"] == "intent-1"
    assert payload["capability_id"] == "capability.inbound.sst-chatbot-agent-handoff"
    assert payload["tenant_id"] == "tenant-1"
    assert payload["user_id"] == "user-1"
    assert payload["idempotency_key"] == "idem-intent-1"
    assert payload["correlation_id"] == "corr-1"
    assert payload["requested_retry_policy"] == "none"
    assert payload["audit_metadata"]["origin_service"] == "sst-chatbot"


def test_validation_rejects_blocked_server_operations() -> None:
    intent = make_record("intent-1").model_copy(
        update={
            "payload": {
                "requested_operation": "server.restart_service",
                "priority": "normal",
            }
        }
    )

    result = validate_record(intent)

    assert result.accepted is False
    assert "blocked_operation" in {issue.code for issue in result.issues}


def test_validation_rejects_downloadable_without_user_visibility() -> None:
    record = make_record("evidence-1", "evidence_ref").model_copy(
        update={"visibility": ("downloadable",)}
    )

    result = validate_record(record)

    assert result.accepted is False
    assert "invalid_visibility" in {issue.code for issue in result.issues}
