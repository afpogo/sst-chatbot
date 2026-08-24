from __future__ import annotations

from typing import cast

import pytest

from app.audience_access.contracts import Audience
from app.audience_access.contracts import DataClassification
from app.audience_access.contracts import MethodologyRecord
from app.audience_access.contracts import MetricClaim
from app.audience_access.contracts import MetricId
from app.audience_access.contracts import MetricQuery
from app.audience_access.contracts import MetricSnapshot
from app.audience_access.contracts import PrincipalContext
from app.audience_access.contracts import PrincipalScope
from app.audience_access.contracts import StakeholderGroundedAnswer
from app.audience_access.methodology import FakeMethodologyRetriever
from app.audience_access.methodology import FakeMethodologySource
from app.audience_access.methodology import FakeStakeholderGroundedAnswerAdapter
from app.audience_access.methodology import StakeholderMethodologySourcePort
from app.audience_access.metrics import FakeStakeholderMetricsAdapter
from app.audience_access.policy import AudiencePolicyEngine
from app.audience_access.policy import POLICY_VERSION
from app.audience_access.policy import STAKEHOLDER_ENTITLEMENT
from app.audience_access.stakeholder_rag import GroundedStakeholderRagRuntime


def stakeholder_principal() -> PrincipalContext:
    return PrincipalContext(
        principal_id="stakeholder-1",
        audience=Audience.SST_STAKEHOLDER,
        scope=PrincipalScope(application_id="sst"),
        entitlements=frozenset({STAKEHOLDER_ENTITLEMENT}),
        asserted_by="sst_backend",
        authentication_ref="session-1",
        policy_version=POLICY_VERSION,
    )


def metric_snapshot(
    *,
    value: int | float | None = 42,
    cohort_size: int = 25,
    provenance: str = "analytics/monthly/v1#2026-07",
) -> MetricSnapshot:
    return MetricSnapshot(
        metric_id=MetricId.ACTIVE_USERS,
        period="2026-07",
        value=value,
        definition="Usuarios con actividad válida durante el mes.",
        cohort_size=cohort_size,
        source="approved_analytics",
        provenance=provenance,
    )


def methodology(
    source_id: str,
    *,
    metric_id: MetricId = MetricId.ACTIVE_USERS,
    content: str = "Una actividad válida aplica la definición owner aprobada.",
    classification: DataClassification = DataClassification.PUBLIC,
    active: bool = True,
    indexable: bool = True,
) -> MethodologyRecord:
    return MethodologyRecord(
        source_id=source_id,
        metric_id=metric_id,
        title=f"Metodología {source_id}",
        content=content,
        classification=classification,
        required_entitlements=frozenset({STAKEHOLDER_ENTITLEMENT}),
        active=active,
        indexable=indexable,
        provenance=f"ards/methodology/{source_id}",
    )


def grounded_answer(
    *,
    value: int | float = 42,
    citations: tuple[str, ...] = ("definition", "calculation"),
    narrative: str = "La métrica sigue la definición y metodología aprobadas.",
) -> StakeholderGroundedAnswer:
    return StakeholderGroundedAnswer(
        narrative=narrative,
        claims=(
            MetricClaim(
                metric_id=MetricId.ACTIVE_USERS,
                period="2026-07",
                value=value,
            ),
        ),
        citation_source_ids=citations,
    )


def runtime(
    *,
    snapshot: MetricSnapshot | None = None,
    records: tuple[MethodologyRecord, ...] | None = None,
    answer: StakeholderGroundedAnswer | None = None,
    metric_available: bool = True,
    methodology_available: bool = True,
    provider_available: bool = True,
) -> tuple[
    GroundedStakeholderRagRuntime,
    FakeMethodologySource,
    FakeMethodologyRetriever,
    FakeStakeholderGroundedAnswerAdapter,
]:
    source = FakeMethodologySource(
        records
        if records is not None
        else (methodology("definition"), methodology("calculation")),
        available=methodology_available,
    )
    retriever = FakeMethodologyRetriever()
    provider = FakeStakeholderGroundedAnswerAdapter(
        answer or grounded_answer(),
        available=provider_available,
    )
    service = GroundedStakeholderRagRuntime(
        policy=AudiencePolicyEngine(),
        metrics=FakeStakeholderMetricsAdapter(
            (snapshot or metric_snapshot(),),
            available=metric_available,
        ),
        methodology_source=source,
        methodology_retriever=retriever,
        provider=provider,
    )
    return service, source, retriever, provider


def explain(service: GroundedStakeholderRagRuntime, question: str = "Explica usuarios activos"):
    return service.explain(
        principal=stakeholder_principal(),
        query=MetricQuery(metric_id=MetricId.ACTIVE_USERS, period="2026-07"),
        question=question,
        correlation_id="corr-1",
    )


def test_grounded_stakeholder_answer_preserves_snapshot_and_citations() -> None:
    service, source, retriever, provider = runtime()

    result = explain(service)

    assert result.accepted
    assert result.code == "grounded_stakeholder_answer"
    assert result.claims[0].value == 42
    assert result.analytics_provenance == "analytics/monthly/v1#2026-07"
    assert {item.source_id for item in result.citations} == {
        "definition",
        "calculation",
    }
    assert source.calls == retriever.calls == provider.calls == 1
    assert provider.last_snapshot == result.snapshot
    assert result.trace.contains_business_data is False
    assert result.handoff_required is False


@pytest.mark.parametrize(
    ("snapshot", "expected_code"),
    [
        (metric_snapshot(cohort_size=9, value=8), "small_cohort_suppressed"),
        (metric_snapshot(provenance=""), "missing_provenance"),
        (metric_snapshot(value=None), "source_suppressed"),
    ],
)
def test_snapshot_gates_stop_before_methodology_and_provider(
    snapshot: MetricSnapshot,
    expected_code: str,
) -> None:
    service, source, retriever, provider = runtime(snapshot=snapshot)

    result = explain(service)

    assert result.code == expected_code
    assert source.calls == retriever.calls == provider.calls == 0
    assert not result.trace.provider_called


def test_metric_source_failure_stops_before_methodology() -> None:
    service, source, retriever, provider = runtime(metric_available=False)

    result = explain(service)

    assert not result.accepted
    assert result.code == "metric_source_unavailable"
    assert source.calls == retriever.calls == provider.calls == 0


def test_only_allowlisted_methodology_reaches_retriever_and_provider() -> None:
    records = (
        methodology("allowed"),
        methodology("restricted", classification=DataClassification.RESTRICTED),
        methodology("inactive", active=False),
        methodology("not-indexed", indexable=False),
        methodology("wrong-metric", metric_id=MetricId.RETENTION_RATE),
        methodology("credential", content="password=not-a-real-password"),
        methodology("person", content="tenant_id=tenant-a"),
    )
    service, _, retriever, provider = runtime(
        records=records,
        answer=grounded_answer(citations=("allowed",)),
    )

    result = explain(service)

    assert result.accepted
    assert [item.source_id for item in retriever.last_input] == ["allowed"]
    assert [item.source_id for item in provider.last_methodology] == ["allowed"]


def test_missing_or_failed_methodology_fails_closed_without_provider() -> None:
    empty_service, _, _, empty_provider = runtime(records=())
    failed_service, _, _, failed_provider = runtime(methodology_available=False)

    empty = explain(empty_service)
    failed = explain(failed_service)

    assert empty.code == "no_authorized_methodology"
    assert failed.code == "methodology_source_error"
    assert empty_provider.calls == failed_provider.calls == 0


@pytest.mark.parametrize(
    ("answer", "expected_code"),
    [
        (grounded_answer(value=99), "unsupported_metric_claim"),
        (grounded_answer(citations=("unknown",)), "unknown_methodology_citation"),
        (
            grounded_answer(narrative="La métrica tiene un valor de 42."),
            "numeric_narrative_forbidden",
        ),
        (
            grounded_answer(narrative="Contactar a ada@example.test."),
            "personal_identifier_detected",
        ),
    ],
)
def test_provider_output_requires_exact_claims_safe_narrative_and_known_citations(
    answer: StakeholderGroundedAnswer,
    expected_code: str,
) -> None:
    service, _, _, provider = runtime(answer=answer)

    result = explain(service)

    assert not result.accepted
    assert result.code == expected_code
    assert provider.calls == 1


def test_forbidden_question_and_provider_failure_are_sanitized() -> None:
    service, source, _, provider = runtime()
    failed_service, _, _, failed_provider = runtime(provider_available=False)

    forbidden = explain(service, "SELECT * FROM conversations")
    failed = explain(failed_service)

    assert forbidden.code == "unsupported_stakeholder_request"
    assert source.calls == provider.calls == 0
    assert failed.code == "provider_error"
    assert failed_provider.calls == 1


def test_malformed_methodology_candidate_becomes_policy_error() -> None:
    class MalformedSource:
        def list_candidates(self, query: MetricQuery):
            return (object(),)

    provider = FakeStakeholderGroundedAnswerAdapter(grounded_answer())
    service = GroundedStakeholderRagRuntime(
        policy=AudiencePolicyEngine(),
        metrics=FakeStakeholderMetricsAdapter((metric_snapshot(),)),
        methodology_source=cast(StakeholderMethodologySourcePort, MalformedSource()),
        methodology_retriever=FakeMethodologyRetriever(),
        provider=provider,
    )

    result = explain(service)

    assert result.code == "methodology_policy_error"
    assert provider.calls == 0
