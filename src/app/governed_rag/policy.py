from __future__ import annotations

import re

from app.audience_access.contracts import DataClassification
from app.governed_rag.contracts import AuthorizedChunk
from app.governed_rag.contracts import GovernedMemoryRecord
from app.governed_rag.contracts import RetrievalScope


POLICY_VERSION = "sst-governed-rag-v1"

_CREDENTIAL_PATTERNS = (
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(
        r"\b(?:api[_-]?key|client[_-]?secret|password|refresh[_-]?token|secret|token)"
        r"\s*[:=]\s*[^\s,;]+",
        re.IGNORECASE,
    ),
)


def contains_credential_like_text(value: str) -> bool:
    return any(pattern.search(value) for pattern in _CREDENTIAL_PATTERNS)


class GovernedRetrievalPolicy:
    """Deterministic authorization that runs before ranking or provider calls."""

    def validate_scope(self, scope: RetrievalScope) -> str | None:
        if scope.policy_version != POLICY_VERSION:
            return "policy_version_mismatch"
        if not scope.tenant_id or not scope.user_id or not scope.application_id:
            return "incomplete_scope"
        if not scope.allowed_sources or not scope.allowed_classifications:
            return "incomplete_scope"
        return None

    def authorize(
        self,
        scope: RetrievalScope,
        record: GovernedMemoryRecord,
    ) -> AuthorizedChunk | None:
        if not record.active or not record.indexable:
            return None
        if (
            record.tenant_id != scope.tenant_id
            or record.user_id != scope.user_id
            or record.application_id != scope.application_id
        ):
            return None
        if record.source not in scope.allowed_sources:
            return None
        if record.classification not in scope.allowed_classifications:
            return None
        if record.classification in {
            DataClassification.RESTRICTED,
            DataClassification.SECRET,
        }:
            return None
        if not record.required_entitlements.issubset(scope.entitlements):
            return None
        if contains_credential_like_text(
            "\n".join(
                (
                    record.record_id,
                    record.source_id,
                    record.title,
                    record.content,
                    record.provenance,
                )
            )
        ):
            return None
        return AuthorizedChunk(
            chunk_id=record.record_id,
            source_id=record.source_id,
            title=record.title,
            content=record.content,
            provenance=record.provenance,
        )
