from __future__ import annotations

from datetime import datetime
from datetime import timezone
import hashlib
import json
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import Field

RecordType = Literal[
    "intent",
    "action",
    "decision",
    "evidence_ref",
    "reminder",
    "runtime_event",
    "visibility_candidate",
    "model_execution",
    "agent_execution",
    "phase_run",
    "validation_result",
]
RecordStatus = Literal[
    "draft",
    "pending",
    "accepted",
    "rejected",
    "running",
    "completed",
    "failed",
    "blocked",
]
VisibilityFlag = Literal["internal", "user_visible", "downloadable", "indexable"]
PhaseName = Literal[
    "capture",
    "classify",
    "local_validate",
    "draft_intent",
    "prepare_handoff",
    "run_provider_adapter",
    "collect_observation",
    "select_visibility",
    "archive_local_record",
    "reject_local_record",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_body_hash(body: dict[str, Any]) -> str:
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class AuditMetadata(BaseModel):
    origin_service: str
    created_by: str
    reason: str
    source: str = ""


class OperationalRecord(BaseModel):
    id: str
    record_type: RecordType
    correlation_id: str
    idempotency_key: str
    producer: str
    audit_metadata: AuditMetadata
    schema_version: str = "1.0"
    tenant_id: str = ""
    scope: str = ""
    user_id: str = ""
    status: RecordStatus = "pending"
    capability_id: str = ""
    phase_name: PhaseName | None = None
    application_id: str = ""
    source_event_id: str = ""
    source_record_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    visibility: tuple[VisibilityFlag, ...] = ("internal",)
    provenance: dict[str, Any] = Field(default_factory=dict)
    body: dict[str, Any] = Field(default_factory=dict)
    body_hash: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)


class ValidationIssue(BaseModel):
    code: str
    message: str
    severity: Literal["error", "warning", "manual-review"] = "error"
    record_id: str = ""


class ValidationResult(BaseModel):
    accepted: bool
    issues: tuple[ValidationIssue, ...] = ()


class PhaseDefinition(BaseModel):
    name: PhaseName
    allowed_next: tuple[PhaseName, ...] = ()
    required_record_types: tuple[RecordType, ...] = ()
    emits: tuple[RecordType, ...] = ("phase_run",)
    requires_human_review: bool = False


class PhaseRunResult(BaseModel):
    phase_run: OperationalRecord
    emitted_records: tuple[OperationalRecord, ...] = ()
    validation: ValidationResult
