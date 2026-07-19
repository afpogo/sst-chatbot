from __future__ import annotations

from pathlib import Path

import yaml

from app.operation_policy import ALLOWED_INITIAL_OPERATIONS
from app.operation_policy import FUTURE_BLOCKED_OPERATIONS
from app.operation_policy import HUMAN_REVIEW_REQUIRED_OPERATIONS
from app.operation_policy import SAFE_INITIAL_OPERATIONS
from app.operation_policy import HANDOFF_CAPABILITY_ID
from app.operation_policy import evaluate_operation


def test_operation_sets_match_the_canonical_boundary_spec() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    path = repo_root / "specs" / "capabilities" / (
        "agent-lifecycle-and-orchestrator-boundary.yaml"
    )
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    policy = spec["operation_intent"]["current_policy"]

    assert SAFE_INITIAL_OPERATIONS == frozenset(policy["safe_initial_types"])
    assert HUMAN_REVIEW_REQUIRED_OPERATIONS == frozenset(
        policy["human_review_required_initial_types"]
    )
    assert FUTURE_BLOCKED_OPERATIONS == frozenset(policy["future_blocked_types"])
    assert ALLOWED_INITIAL_OPERATIONS == frozenset(
        spec["operation_intent"]["initial_types"]
    )
    assert HANDOFF_CAPABILITY_ID == spec["orchestrator_link"]["capability_id"]


def test_missing_unknown_and_blocked_operations_are_rejected() -> None:
    assert evaluate_operation(None).code == "missing_requested_operation"
    assert evaluate_operation("totally.unknown").code == "unsupported_operation"
    assert evaluate_operation("server.restart_service").code == "blocked_operation"


def test_review_operation_requires_review_and_safe_operation_does_not() -> None:
    assert evaluate_operation("workspace.apply_patch").code == "human_review_required"
    assert evaluate_operation(
        "workspace.apply_patch",
        human_reviewed=True,
    ).accepted
    assert evaluate_operation("workspace.generate_bundle").accepted
