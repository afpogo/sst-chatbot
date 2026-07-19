from __future__ import annotations

from app.operation_policy import HANDOFF_CAPABILITY_ID
from app.operation_policy import evaluate_operation
from app.orchestrator.types import HandoffDecision
from app.orchestrator.types import HandoffIssue
from app.orchestrator.types import HandoffPayload

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

    if payload.capability_id and payload.capability_id != HANDOFF_CAPABILITY_ID:
        issues.append(
            HandoffIssue(
                code="unsupported_capability",
                message=f"{payload.capability_id} is not the configured handoff capability",
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

    operation_decision = evaluate_operation(
        payload.payload.get("requested_operation"),
        human_reviewed=human_reviewed,
    )
    if not operation_decision.accepted:
        issues.append(
            HandoffIssue(
                code=operation_decision.code,
                message=operation_decision.message,
                severity=(
                    "manual-review"
                    if operation_decision.code == "human_review_required"
                    else "error"
                ),
            )
        )

    if issues:
        return HandoffDecision(
            accepted=False,
            status="rejected_by_policy",
            issues=tuple(issues),
        )

    return HandoffDecision(accepted=True, status="accepted_for_review")
