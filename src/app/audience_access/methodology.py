from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Protocol

from app.audience_access.contracts import AuthorizedMethodology
from app.audience_access.contracts import MethodologyRecord
from app.audience_access.contracts import MetricQuery
from app.audience_access.contracts import MetricSnapshot
from app.audience_access.contracts import StakeholderGroundedAnswer


class MethodologySourceUnavailable(RuntimeError):
    """The owner-controlled methodology source could not be read."""


class StakeholderMethodologySourcePort(Protocol):
    def list_candidates(self, query: MetricQuery) -> Iterable[MethodologyRecord]:
        """Return candidates; authorization still belongs to the runtime policy."""


class MethodologyRetrieverPort(Protocol):
    def retrieve(
        self,
        *,
        question: str,
        methodology: tuple[AuthorizedMethodology, ...],
        limit: int,
    ) -> tuple[AuthorizedMethodology, ...]:
        """Rank only the methodology projection already authorized by policy."""


class StakeholderGroundedAnswerPort(Protocol):
    def answer(
        self,
        *,
        question: str,
        snapshot: MetricSnapshot,
        methodology: tuple[AuthorizedMethodology, ...],
        correlation_id: str,
    ) -> StakeholderGroundedAnswer:
        """Return structured claims and citations without receiving a principal."""


class FakeMethodologySource:
    def __init__(
        self,
        records: tuple[MethodologyRecord, ...] = (),
        *,
        available: bool = True,
    ) -> None:
        self._records = records
        self._available = available
        self.calls = 0

    def list_candidates(self, query: MetricQuery) -> Iterable[MethodologyRecord]:
        self.calls += 1
        if not self._available:
            raise MethodologySourceUnavailable("methodology source is unavailable")
        return self._records


class FakeMethodologyRetriever:
    """Deterministic lexical ranker for local tests; it grants no access."""

    def __init__(self) -> None:
        self.calls = 0
        self.last_input: tuple[AuthorizedMethodology, ...] = ()

    def retrieve(
        self,
        *,
        question: str,
        methodology: tuple[AuthorizedMethodology, ...],
        limit: int,
    ) -> tuple[AuthorizedMethodology, ...]:
        self.calls += 1
        self.last_input = methodology
        terms = set(re.findall(r"[a-z0-9_]+", question.lower()))

        def rank(item: AuthorizedMethodology) -> tuple[int, str]:
            haystack = f"{item.title} {item.content}".lower()
            score = sum(term in haystack for term in terms)
            return (-score, item.source_id)

        return tuple(sorted(methodology, key=rank)[:limit])


class FakeStakeholderGroundedAnswerAdapter:
    def __init__(
        self,
        answer: StakeholderGroundedAnswer,
        *,
        available: bool = True,
    ) -> None:
        self._answer = answer
        self._available = available
        self.calls = 0
        self.last_snapshot: MetricSnapshot | None = None
        self.last_methodology: tuple[AuthorizedMethodology, ...] = ()

    def answer(
        self,
        *,
        question: str,
        snapshot: MetricSnapshot,
        methodology: tuple[AuthorizedMethodology, ...],
        correlation_id: str,
    ) -> StakeholderGroundedAnswer:
        self.calls += 1
        self.last_snapshot = snapshot
        self.last_methodology = methodology
        if not self._available:
            raise RuntimeError("provider is unavailable")
        return self._answer
