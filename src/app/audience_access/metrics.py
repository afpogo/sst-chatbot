from __future__ import annotations

from typing import Protocol

from app.audience_access.contracts import MetricQuery
from app.audience_access.contracts import MetricSnapshot


class MetricSourceUnavailable(RuntimeError):
    """The approved analytical source could not produce a safe snapshot."""


class StakeholderMetricsPort(Protocol):
    def fetch_snapshot(self, query: MetricQuery) -> MetricSnapshot:
        """Return one global, aggregate snapshot for an approved query."""


def metric_query_key(query: MetricQuery) -> tuple[str, str, str, str]:
    return (
        query.metric_id.value,
        query.period,
        query.dimension or "",
        query.dimension_value or "",
    )


class FakeStakeholderMetricsAdapter:
    """Deterministic local adapter; it never calls a database or service."""

    def __init__(
        self,
        snapshots: tuple[MetricSnapshot, ...] = (),
        *,
        available: bool = True,
    ) -> None:
        self._available = available
        self._snapshots = {
            (
                snapshot.metric_id.value,
                snapshot.period,
                snapshot.dimension or "",
                snapshot.dimension_value or "",
            ): snapshot
            for snapshot in snapshots
        }

    def fetch_snapshot(self, query: MetricQuery) -> MetricSnapshot:
        if not self._available:
            raise MetricSourceUnavailable("approved analytics source is unavailable")
        try:
            return self._snapshots[metric_query_key(query)]
        except KeyError as exc:
            raise MetricSourceUnavailable("approved metric snapshot was not found") from exc
