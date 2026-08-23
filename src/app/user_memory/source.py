from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.audience_access.contracts import DataClassification
from app.governed_rag.contracts import GovernedMemoryRecord
from app.governed_rag.contracts import RetrievalScope
from app.user_memory.bend_client import BendUserMemoryClient
from app.user_memory.contracts import MemoryProposalCandidate
from app.user_memory.contracts import MemoryProposalReceipt
from app.user_memory.contracts import UserMemoryPortError


class BendConversationMemorySource:
    """Turn-bound source; Bend, not the caller, supplies authoritative scope."""

    def __init__(
        self,
        *,
        client: BendUserMemoryClient,
        conversation_ref: str,
        correlation_id: str,
    ) -> None:
        self.client = client
        self.conversation_ref = conversation_ref
        self.correlation_id = correlation_id

    def list_candidates(self, scope: RetrievalScope) -> Iterable[GovernedMemoryRecord]:
        response = self.client.recall_candidates(
            conversation_ref=self.conversation_ref,
            correlation_id=self.correlation_id,
        )
        authoritative = response["scope"]
        expected = {
            "tenantId": scope.tenant_id,
            "userId": scope.user_id,
            "applicationId": scope.application_id,
        }
        if authoritative != expected:
            raise UserMemoryPortError("Bend memory scope does not match the validated turn")
        return tuple(self._record(item, authoritative) for item in response["records"])

    def audit_recall(self, record_ids: list[str], citations: list[dict[str, str]]) -> None:
        self.client.audit_recall(
            conversation_ref=self.conversation_ref,
            correlation_id=self.correlation_id,
            retrieved_memory_ids=record_ids,
            citation_refs=citations,
        )

    def propose(self, *, idempotency_key: str, candidate: MemoryProposalCandidate) -> MemoryProposalReceipt:
        return self.client.propose(
            conversation_ref=self.conversation_ref,
            correlation_id=self.correlation_id,
            idempotency_key=idempotency_key,
            candidate=candidate,
        )

    @staticmethod
    def _record(item: Any, scope: dict[str, str]) -> GovernedMemoryRecord:
        if not isinstance(item, dict):
            raise UserMemoryPortError("Bend returned an invalid memory record")
        content = item.get("content") or {}
        kind = item.get("kind")
        if kind == "fact":
            title, text = "Hecho recordado", content.get("statement")
        elif kind == "intention":
            title, text = "Intencion recordada", content.get("intentText")
        elif kind == "thread":
            title = content.get("title")
            text = content.get("summary") or title
        else:
            raise UserMemoryPortError("Bend returned an unsupported memory kind")
        visibility = item.get("visibility") or {}
        record_id = item.get("id")
        revision = item.get("revision", 1)
        try:
            classification = DataClassification(item.get("classification"))
            return GovernedMemoryRecord(
                record_id=record_id,
                source_id=record_id,
                source="user_memory",
                title=title,
                content=text,
                tenant_id=scope["tenantId"],
                user_id=scope["userId"],
                application_id=scope["applicationId"],
                classification=classification,
                required_entitlements=frozenset(),
                active=item.get("status") == "active",
                indexable=visibility.get("indexable") is True and visibility.get("providerEligible") is True,
                provenance=f"memory:{record_id}:r{revision}",
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise UserMemoryPortError("Bend returned an invalid memory record") from exc
