from __future__ import annotations

from app.governed_rag.contracts import Citation
from app.governed_rag.contracts import DecisionTrace
from app.governed_rag.contracts import GroundedAnswer
from app.governed_rag.contracts import ProviderContext
from app.governed_rag.contracts import RagResult
from app.governed_rag.contracts import RagStatus
from app.governed_rag.contracts import RankedChunk
from app.governed_rag.contracts import RetrievalScope
from app.governed_rag.policy import GovernedRetrievalPolicy
from app.governed_rag.policy import contains_credential_like_text
from app.governed_rag.ports import GovernedMemorySourcePort
from app.governed_rag.ports import GroundedAnswerPort
from app.governed_rag.ports import RetrieverPort


class GovernedRagRuntime:
    """Read-only, transport-neutral RAG pipeline with fail-closed boundaries."""

    def __init__(
        self,
        *,
        source: GovernedMemorySourcePort,
        retriever: RetrieverPort,
        provider: GroundedAnswerPort,
        policy: GovernedRetrievalPolicy | None = None,
        retrieval_limit: int = 3,
        minimum_score: float = 1.0,
        max_context_characters: int = 6000,
    ) -> None:
        if retrieval_limit <= 0:
            raise ValueError("retrieval_limit must be greater than zero")
        if minimum_score <= 0:
            raise ValueError("minimum_score must be greater than zero")
        if max_context_characters <= 0:
            raise ValueError("max_context_characters must be greater than zero")
        self._source = source
        self._retriever = retriever
        self._provider = provider
        self._policy = policy or GovernedRetrievalPolicy()
        self._retrieval_limit = retrieval_limit
        self._minimum_score = minimum_score
        self._max_context_characters = max_context_characters

    def answer(
        self,
        *,
        question: str,
        scope: RetrievalScope,
        correlation_id: str,
    ) -> RagResult:
        clean_question = question.strip()
        if not correlation_id.strip():
            raise ValueError("correlation_id is required")
        if not clean_question:
            return self._result(
                RagStatus.DENIED,
                "empty_question",
                correlation_id,
            )
        scope_error = self._policy.validate_scope(scope)
        if scope_error:
            return self._result(RagStatus.DENIED, scope_error, correlation_id)
        if contains_credential_like_text(clean_question):
            return self._result(
                RagStatus.DENIED,
                "sensitive_question_detected",
                correlation_id,
            )

        try:
            candidates = tuple(self._source.list_candidates(scope))
        except Exception:
            return self._result(RagStatus.ERROR, "source_error", correlation_id)

        try:
            authorized = tuple(
                chunk
                for record in candidates
                if (chunk := self._policy.authorize(scope, record)) is not None
            )
        except Exception:
            return self._result(
                RagStatus.ERROR,
                "policy_error",
                correlation_id,
                candidate_count=len(candidates),
            )
        if not authorized:
            return self._result(
                RagStatus.INSUFFICIENT_CONTEXT,
                "no_authorized_context",
                correlation_id,
                candidate_count=len(candidates),
            )

        try:
            ranked = self._retriever.retrieve(
                query=clean_question,
                chunks=authorized,
                limit=self._retrieval_limit,
                minimum_score=self._minimum_score,
            )
        except Exception:
            return self._result(
                RagStatus.ERROR,
                "retriever_error",
                correlation_id,
                candidate_count=len(candidates),
                authorized_count=len(authorized),
            )

        bounded = self._within_budget(ranked)
        if not bounded:
            return self._result(
                RagStatus.INSUFFICIENT_CONTEXT,
                "insufficient_context",
                correlation_id,
                candidate_count=len(candidates),
                authorized_count=len(authorized),
            )

        provider_context = tuple(
            ProviderContext(
                chunk_id=item.chunk.chunk_id,
                title=item.chunk.title,
                content=item.chunk.content,
            )
            for item in bounded
        )
        try:
            answer = self._provider.answer(
                question=clean_question,
                context=provider_context,
                correlation_id=correlation_id,
            )
        except Exception:
            return self._result(
                RagStatus.ERROR,
                "provider_error",
                correlation_id,
                candidate_count=len(candidates),
                authorized_count=len(authorized),
                retrieved_count=len(bounded),
            )

        try:
            validation_error = self._validate_answer(answer, bounded)
        except Exception:
            validation_error = "invalid_provider_output"
        if validation_error:
            return self._result(
                RagStatus.DENIED,
                validation_error,
                correlation_id,
                candidate_count=len(candidates),
                authorized_count=len(authorized),
                retrieved_count=len(bounded),
            )

        by_id = {item.chunk.chunk_id: item.chunk for item in bounded}
        cited_ids = tuple(
            dict.fromkeys(
                chunk_id
                for claim in answer.claims
                for chunk_id in claim.citation_chunk_ids
            )
        )
        citations = tuple(
            Citation(
                chunk_id=by_id[chunk_id].chunk_id,
                source_id=by_id[chunk_id].source_id,
                title=by_id[chunk_id].title,
                provenance=by_id[chunk_id].provenance,
            )
            for chunk_id in cited_ids
        )
        return self._result(
            RagStatus.COMPLETED,
            "grounded_answer",
            correlation_id,
            answer=" ".join(claim.text.strip() for claim in answer.claims),
            citations=citations,
            candidate_count=len(candidates),
            authorized_count=len(authorized),
            retrieved_count=len(bounded),
        )

    def _within_budget(self, ranked: tuple[RankedChunk, ...]) -> tuple[RankedChunk, ...]:
        selected: list[RankedChunk] = []
        consumed = 0
        for item in ranked:
            size = len(item.chunk.title) + len(item.chunk.content)
            if consumed + size > self._max_context_characters:
                continue
            selected.append(item)
            consumed += size
        return tuple(selected)

    @staticmethod
    def _validate_answer(
        answer: GroundedAnswer,
        ranked: tuple[RankedChunk, ...],
    ) -> str | None:
        allowed_ids = {item.chunk.chunk_id for item in ranked}
        for claim in answer.claims:
            if contains_credential_like_text(claim.text):
                return "sensitive_provider_output"
            if not claim.citation_chunk_ids:
                return "uncited_claim"
            if not set(claim.citation_chunk_ids).issubset(allowed_ids):
                return "unknown_citation"
        return None

    @staticmethod
    def _result(
        status: RagStatus,
        code: str,
        correlation_id: str,
        *,
        answer: str = "",
        citations: tuple[Citation, ...] = (),
        candidate_count: int = 0,
        authorized_count: int = 0,
        retrieved_count: int = 0,
    ) -> RagResult:
        return RagResult(
            status=status,
            decision_code=code,
            answer=answer,
            citations=citations,
            trace=DecisionTrace(
                correlation_id=correlation_id,
                decision_code=code,
                candidate_count=candidate_count,
                authorized_count=authorized_count,
                retrieved_count=retrieved_count,
            ),
        )
