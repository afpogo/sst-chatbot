from __future__ import annotations

from dataclasses import dataclass


HANDOFF_CAPABILITY_ID = "capability.inbound.sst-chatbot-agent-handoff"

SAFE_INITIAL_OPERATIONS = frozenset(
    {
        "workspace.generate_bundle",
        "user_history.propose_update",
        "ui_customization.enqueue_change",
    }
)
HUMAN_REVIEW_REQUIRED_OPERATIONS = frozenset({"workspace.apply_patch"})
ALLOWED_INITIAL_OPERATIONS = (
    SAFE_INITIAL_OPERATIONS | HUMAN_REVIEW_REQUIRED_OPERATIONS
)
FUTURE_BLOCKED_OPERATIONS = frozenset(
    {"server.restart_service", "server.refresh_cache"}
)


@dataclass(frozen=True)
class OperationPolicyDecision:
    accepted: bool
    code: str = ""
    message: str = ""


def evaluate_operation(
    requested_operation: object,
    *,
    human_reviewed: bool = False,
) -> OperationPolicyDecision:
    if not isinstance(requested_operation, str) or not requested_operation.strip():
        return OperationPolicyDecision(
            accepted=False,
            code="missing_requested_operation",
            message="payload.requested_operation is required",
        )

    if requested_operation in FUTURE_BLOCKED_OPERATIONS:
        return OperationPolicyDecision(
            accepted=False,
            code="blocked_operation",
            message=(
                f"{requested_operation} is blocked until RBAC, audit, rollback, "
                "scheduling policy, and approval gates exist"
            ),
        )

    if requested_operation not in ALLOWED_INITIAL_OPERATIONS:
        return OperationPolicyDecision(
            accepted=False,
            code="unsupported_operation",
            message=f"{requested_operation} is not an allowed initial operation",
        )

    if (
        requested_operation in HUMAN_REVIEW_REQUIRED_OPERATIONS
        and not human_reviewed
    ):
        return OperationPolicyDecision(
            accepted=False,
            code="human_review_required",
            message=f"{requested_operation} requires human review",
        )

    return OperationPolicyDecision(accepted=True)
