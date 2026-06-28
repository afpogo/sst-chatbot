from __future__ import annotations

from typing import Any

from app.memory.types import OperationalRecord
from app.memory.validation import require_valid_record


def to_operation_intent(record: OperationalRecord) -> dict[str, Any]:
    require_valid_record(record)
    if record.record_type != "intent":
        raise ValueError("operation_intent requires an intent record")

    return {
        "operation_intent_id": record.id,
        "capability_id": record.capability_id,
        "tenant_id": record.tenant_id or record.scope,
        "user_id": record.user_id,
        "payload": record.payload,
        "priority": record.payload.get("priority", "normal"),
        "preferred_execution_window": record.payload.get(
            "preferred_execution_window",
            "manual",
        ),
        "idempotency_key": record.idempotency_key,
        "correlation_id": record.correlation_id,
    }


def to_handoff_payload(record: OperationalRecord) -> dict[str, Any]:
    operation_intent = to_operation_intent(record)
    return {
        **operation_intent,
        "requested_retry_policy": record.payload.get("requested_retry_policy", "none"),
        "audit_metadata": {
            "origin_service": record.audit_metadata.origin_service,
            "created_at": record.created_at,
            "created_by": record.audit_metadata.created_by,
            "reason": record.audit_metadata.reason,
        },
    }


def to_agent_result(record: OperationalRecord) -> dict[str, Any]:
    require_valid_record(record)
    if record.record_type != "agent_execution":
        raise ValueError("agent_result requires an agent_execution record")

    return {
        "result_id": record.id,
        "operation_intent_id": record.source_record_ids[0]
        if record.source_record_ids
        else "",
        "capability_id": record.capability_id,
        "tenant_id": record.tenant_id or record.scope,
        "status": record.status,
        "structured_output": record.payload,
        "validation_summary": {
            "accepted": record.status == "completed",
            "issues": [],
        },
        "correlation_id": record.correlation_id,
    }
