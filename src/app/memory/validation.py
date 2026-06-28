from __future__ import annotations

from app.memory.types import OperationalRecord
from app.memory.types import ValidationIssue
from app.memory.types import ValidationResult
from app.memory.types import stable_body_hash

BLOCKED_OPERATIONS = {"server.restart_service", "server.refresh_cache"}


def validate_record(record: OperationalRecord) -> ValidationResult:
    issues: list[ValidationIssue] = []

    required_fields = (
        ("id", record.id),
        ("correlation_id", record.correlation_id),
        ("idempotency_key", record.idempotency_key),
        ("producer", record.producer),
        ("audit_metadata.origin_service", record.audit_metadata.origin_service),
        ("audit_metadata.created_by", record.audit_metadata.created_by),
        ("audit_metadata.reason", record.audit_metadata.reason),
    )

    for field_name, value in required_fields:
        if not value:
            issues.append(
                ValidationIssue(
                    code="missing_required_field",
                    message=f"{field_name} is required",
                    record_id=record.id,
                )
            )

    if not record.tenant_id and not record.scope:
        issues.append(
            ValidationIssue(
                code="missing_scope",
                message="tenant_id or scope is required",
                record_id=record.id,
            )
        )

    if record.body:
        expected_hash = stable_body_hash(record.body)
        if not record.body_hash:
            issues.append(
                ValidationIssue(
                    code="missing_body_hash",
                    message="body_hash is required when body is present",
                    record_id=record.id,
                )
            )
        elif record.body_hash != expected_hash:
            issues.append(
                ValidationIssue(
                    code="body_hash_mismatch",
                    message="body_hash must match the canonical body hash",
                    record_id=record.id,
                )
            )

    if record.visibility and "downloadable" in record.visibility:
        if "user_visible" not in record.visibility:
            issues.append(
                ValidationIssue(
                    code="invalid_visibility",
                    message="downloadable records must also be user_visible",
                    record_id=record.id,
                )
            )

    requested_operation = record.payload.get("requested_operation")
    if requested_operation in BLOCKED_OPERATIONS:
        issues.append(
            ValidationIssue(
                code="blocked_operation",
                message=f"{requested_operation} is blocked until RBAC, audit, rollback, scheduling policy, and approval gates exist",
                record_id=record.id,
            )
        )

    return ValidationResult(accepted=not issues, issues=tuple(issues))


def require_valid_record(record: OperationalRecord) -> None:
    result = validate_record(record)
    if not result.accepted:
        messages = "; ".join(issue.message for issue in result.issues)
        raise ValueError(messages)
