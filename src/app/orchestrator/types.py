from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import Field

HandoffStatus = Literal[
    "received",
    "accepted_for_review",
    "rejected_by_policy",
    "duplicate",
    "conflict",
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


class ReviewEvidence(BaseModel):
    model_config = {"frozen": True}

    reviewer: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    evidence_ref: str = Field(min_length=1)
    reviewed_at: datetime = Field(default_factory=_utc_now)


class HandoffPayload(BaseModel):
    operation_intent_id: str
    capability_id: str
    tenant_id: str
    user_id: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: str = "normal"
    preferred_execution_window: str = "manual"
    requested_retry_policy: str = "none"
    idempotency_key: str
    correlation_id: str
    audit_metadata: dict[str, Any] = Field(default_factory=dict)


class HandoffIssue(BaseModel):
    code: str
    message: str
    severity: Literal["error", "warning", "manual-review"] = "error"


class HandoffDecision(BaseModel):
    accepted: bool
    status: HandoffStatus
    issues: tuple[HandoffIssue, ...] = ()


class HandoffReceipt(BaseModel):
    receipt_id: str
    status: HandoffStatus
    operation_intent_id: str
    capability_id: str
    tenant_id: str
    user_id: str = ""
    idempotency_key: str
    correlation_id: str
    audit_metadata: dict[str, Any] = Field(default_factory=dict)
    review_evidence: ReviewEvidence | None = None
    decision: HandoffDecision
    payload_fingerprint: str
