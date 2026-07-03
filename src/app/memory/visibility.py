from __future__ import annotations

from app.memory.types import AuditMetadata
from app.memory.types import OperationalRecord


def build_visibility_candidates(
    records: tuple[OperationalRecord, ...],
) -> tuple[OperationalRecord, ...]:
    candidates: list[OperationalRecord] = []

    for record in records:
        reason = _visibility_reason(record)
        if not reason:
            continue
        candidates.append(
            OperationalRecord(
                id=f"visibility-{record.id}",
                record_type="visibility_candidate",
                tenant_id=record.tenant_id,
                scope=record.scope,
                user_id=record.user_id,
                correlation_id=record.correlation_id,
                idempotency_key=f"visibility:{record.id}",
                producer="sst-chatbot",
                capability_id=record.capability_id,
                source_record_ids=(record.id,),
                status="pending",
                audit_metadata=AuditMetadata(
                    origin_service="sst-chatbot",
                    created_by="visibility-selector",
                    reason=reason,
                ),
                payload={
                    "source_record_type": record.record_type,
                    "source_status": record.status,
                    "reason": reason,
                },
            )
        )

    return tuple(candidates)


def _visibility_reason(record: OperationalRecord) -> str:
    if record.record_type == "reminder" and record.status in {"pending", "blocked"}:
        return "pending reminder should remain visible"
    if record.record_type == "decision" and record.status in {"pending", "accepted"}:
        return "decision is likely to be forgotten"
    if record.record_type == "validation_result" and record.status in {
        "failed",
        "blocked",
        "rejected",
    }:
        return "validation issue requires attention"
    if record.record_type == "evidence_ref" and record.status == "pending":
        return "pending evidence must be resolved"
    return ""
