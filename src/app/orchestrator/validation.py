from __future__ import annotations

from typing import Any

from app.orchestrator.types import HandoffDecision
from app.orchestrator.types import HandoffIssue
from app.orchestrator.types import HandoffPayload

BLOCKED_OPERATIONS = {"server.restart_service", "server.refresh_cache"}
HUMAN_REVIEW_REQUIRED_OPERATIONS = {"workspace.apply_patch"}


def validate_handoff_payload(
    payload: HandoffPayload,
    *,
    human_reviewed: bool = False,
) -> HandoffDecision:
    issues: list[HandoffIssue] = []

    required_fields = (
        ("operation_intent_id", payload.operation_intent_id),
        ("capability_id", payload.capability_id),
        ("tenant_id", payload.tenant_id),
        ("idempotency_key", payload.idempotency_key),
        ("correlation_id", payload.correlation_id),
    )
    for field_name, value in required_fields:
        if not value:
            issues.append(
                HandoffIssue(
                    code="missing_required_field",
                    message=f"{field_name} is required",
                )
            )

    audit = payload.audit_metadata
    for field_name in ("origin_service", "created_at", "created_by", "reason"):
        if not audit.get(field_name):
            issues.append(
                HandoffIssue(
                    code="missing_audit_metadata",
                    message=f"audit_metadata.{field_name} is required",
                )
            )

    requested_operation = _requested_operation(payload.payload)
    if requested_operation in BLOCKED_OPERATIONS:
        issues.append(
            HandoffIssue(
                code="blocked_operation",
                message=f"{requested_operation} is blocked for local fake handoff",
            )
        )

    if (
        requested_operation in HUMAN_REVIEW_REQUIRED_OPERATIONS
        and not human_reviewed
    ):
        issues.append(
            HandoffIssue(
                code="human_review_required",
                message=f"{requested_operation} requires human review",
                severity="manual-review",
            )
        )

    if issues:
        return HandoffDecision(
            accepted=False,
            status="rejected_by_policy",
            issues=tuple(issues),
        )

    return HandoffDecision(accepted=True, status="accepted_for_review")


def _requested_operation(payload: dict[str, Any]) -> str:
    value = payload.get("requested_operation")
    if isinstance(value, str):
        return value
    return ""
