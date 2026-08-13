from __future__ import annotations

from collections.abc import Iterable

from app.governed_rag.contracts import GovernedMemoryRecord
from app.governed_rag.contracts import GroundedAnswer
from app.governed_rag.contracts import GroundedClaim
from app.governed_rag.contracts import ProviderContext
from app.governed_rag.contracts import RetrievalScope


class InMemoryGovernedMemorySource:
    """Test source intentionally able to return mixed-scope candidates."""

    def __init__(self, records: Iterable[GovernedMemoryRecord]) -> None:
        self.records = tuple(records)
        self.calls: list[RetrievalScope] = []

    def list_candidates(self, scope: RetrievalScope):
        self.calls.append(scope)
        return self.records


class RecordingGroundedAnswerProvider:
    def __init__(
        self,
        answer: GroundedAnswer | None = None,
        *,
        failure: Exception | None = None,
    ) -> None:
        self.response = answer
        self.failure = failure
        self.calls: list[dict[str, object]] = []

    def answer(
        self,
        *,
        question: str,
        context: tuple[ProviderContext, ...],
        correlation_id: str,
    ) -> GroundedAnswer:
        self.calls.append(
            {
                "question": question,
                "context": context,
                "correlation_id": correlation_id,
            }
        )
        if self.failure is not None:
            raise self.failure
        if self.response is not None:
            return self.response
        claims = tuple(
            GroundedClaim(
                text=f"Contexto verificado en {item.title}.",
                citation_chunk_ids=(item.chunk_id,),
            )
            for item in context
        )
        return GroundedAnswer(claims=claims)
