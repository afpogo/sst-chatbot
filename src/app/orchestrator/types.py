from __future__ import annotations

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
    decision: HandoffDecision
    payload_fingerprint: str
