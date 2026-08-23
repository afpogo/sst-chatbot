from __future__ import annotations

import hashlib
from collections.abc import Callable
from uuid import uuid4

from app.audience_access.contracts import DataClassification
from app.chat_runtime.port import RuntimeEvent
from app.chat_runtime.port import TurnRequest
from app.governed_rag.contracts import RagStatus
from app.governed_rag.contracts import RetrievalScope
from app.governed_rag.policy import POLICY_VERSION
from app.governed_rag.runtime import GovernedRagRuntime
from app.user_memory.bend_client import BendUserMemoryClient
from app.user_memory.contracts import MemoryProposalBuilderPort
from app.user_memory.source import BendConversationMemorySource


class GovernedMemoryChatRuntime:
    """Composes recall, grounded answer, recall audit and review-only proposal."""

    def __init__(
        self,
        *,
        client: BendUserMemoryClient,
        rag_factory: Callable[[BendConversationMemorySource], GovernedRagRuntime],
        proposal_builder: MemoryProposalBuilderPort,
    ) -> None:
        self._client = client
        self._rag_factory = rag_factory
        self._proposal_builder = proposal_builder

    def process_turn(self, request: TurnRequest):
        source = BendConversationMemorySource(
            client=self._client,
            conversation_ref=request.conversation_id,
            correlation_id=request.correlation_id,
        )
        scope = RetrievalScope(
            tenant_id=request.principal.tenant_id,
            user_id=request.principal.user_id,
            application_id="sst",
            entitlements=frozenset(),
            allowed_classifications=frozenset(
                {DataClassification.PUBLIC, DataClassification.INTERNAL, DataClassification.PRIVATE}
            ),
            allowed_sources=frozenset({"user_memory"}),
            policy_version=POLICY_VERSION,
        )
        result = self._rag_factory(source).answer(
            question=request.text,
            scope=scope,
            correlation_id=request.correlation_id,
        )
        if result.status is not RagStatus.COMPLETED:
            yield RuntimeEvent(
                type="completed",
                text="",
                message_id=str(uuid4()),
                correlation_id=request.correlation_id,
                code=result.decision_code,
            )
            return

        record_ids = list(dict.fromkeys(citation.chunk_id for citation in result.citations))
        source.audit_recall(
            record_ids,
            [
                {"memoryId": citation.chunk_id, "ref": citation.provenance}
                for citation in result.citations
            ],
        )
        candidate = self._proposal_builder.build_candidate(
            question=request.text,
            answer=result.answer,
            citations=result.citations,
            correlation_id=request.correlation_id,
        )
        if candidate is not None:
            digest = hashlib.sha256(
                f"{request.conversation_id}:{request.message_id}".encode()
            ).hexdigest()
            receipt = source.propose(
                idempotency_key=f"chat-memory:{digest}",
                candidate=candidate,
            )
            yield RuntimeEvent(
                type="memory_proposal",
                code=receipt.status,
                message_id=receipt.id,
                correlation_id=request.correlation_id,
            )
        yield RuntimeEvent(type="delta", text=result.answer)
        yield RuntimeEvent(
            type="completed",
            text=result.answer,
            message_id=str(uuid4()),
            correlation_id=request.correlation_id,
            code=result.decision_code,
        )
