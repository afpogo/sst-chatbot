from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from app.governed_rag.contracts import AuthorizedChunk
from app.governed_rag.contracts import GovernedMemoryRecord
from app.governed_rag.contracts import GroundedAnswer
from app.governed_rag.contracts import ProviderContext
from app.governed_rag.contracts import RankedChunk
from app.governed_rag.contracts import RetrievalScope


class GovernedMemorySourcePort(Protocol):
    def list_candidates(self, scope: RetrievalScope) -> Iterable[GovernedMemoryRecord]:
        """Return candidates; the runtime still applies its own fail-closed policy."""


class RetrieverPort(Protocol):
    def retrieve(
        self,
        *,
        query: str,
        chunks: tuple[AuthorizedChunk, ...],
        limit: int,
        minimum_score: float,
    ) -> tuple[RankedChunk, ...]:
        """Rank only chunks already authorized by the policy boundary."""


class GroundedAnswerPort(Protocol):
    def answer(
        self,
        *,
        question: str,
        context: tuple[ProviderContext, ...],
        correlation_id: str,
    ) -> GroundedAnswer:
        """Return claims whose citations refer to supplied context chunk IDs."""
