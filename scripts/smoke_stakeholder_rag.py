from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from app.audience_access.contracts import Audience  # noqa: E402
from app.audience_access.contracts import DataClassification  # noqa: E402
from app.audience_access.contracts import MethodologyRecord  # noqa: E402
from app.audience_access.contracts import MetricClaim  # noqa: E402
from app.audience_access.contracts import MetricId  # noqa: E402
from app.audience_access.contracts import MetricQuery  # noqa: E402
from app.audience_access.contracts import MetricSnapshot  # noqa: E402
from app.audience_access.contracts import PrincipalContext  # noqa: E402
from app.audience_access.contracts import PrincipalScope  # noqa: E402
from app.audience_access.contracts import StakeholderGroundedAnswer  # noqa: E402
from app.audience_access.methodology import FakeMethodologyRetriever  # noqa: E402
from app.audience_access.methodology import FakeMethodologySource  # noqa: E402
from app.audience_access.methodology import FakeStakeholderGroundedAnswerAdapter  # noqa: E402
from app.audience_access.metrics import FakeStakeholderMetricsAdapter  # noqa: E402
from app.audience_access.policy import AudiencePolicyEngine  # noqa: E402
from app.audience_access.policy import POLICY_VERSION  # noqa: E402
from app.audience_access.policy import STAKEHOLDER_ENTITLEMENT  # noqa: E402
from app.audience_access.stakeholder_rag import GroundedStakeholderRagRuntime  # noqa: E402


def run_smoke() -> dict[str, object]:
    principal = PrincipalContext(
        principal_id="stakeholder-smoke",
        audience=Audience.SST_STAKEHOLDER,
        scope=PrincipalScope(application_id="sst"),
        entitlements=frozenset({STAKEHOLDER_ENTITLEMENT}),
        asserted_by="sst_backend",
        authentication_ref="smoke-session",
        policy_version=POLICY_VERSION,
    )
    query = MetricQuery(metric_id=MetricId.ACTIVE_USERS, period="2026-07")
    snapshot = MetricSnapshot(
        metric_id=query.metric_id,
        period=query.period,
        value=42,
        definition="Accounts with an active user in the monthly period.",
        cohort_size=42,
        provenance="approved-analytics:active-users:2026-07",
    )
    methodology = MethodologyRecord(
        source_id="active-users-method-v1",
        metric_id=query.metric_id,
        title="Active users methodology",
        content="Counts unique active accounts within the closed monthly period.",
        classification=DataClassification.DERIVED_SAFE,
        required_entitlements=frozenset({STAKEHOLDER_ENTITLEMENT}),
        active=True,
        indexable=True,
        provenance="methodology:active-users:v1",
    )
    source = FakeMethodologySource((methodology,))
    retriever = FakeMethodologyRetriever()
    provider = FakeStakeholderGroundedAnswerAdapter(
        StakeholderGroundedAnswer(
            narrative="La métrica sigue la metodología mensual aprobada.",
            claims=(
                MetricClaim(
                    metric_id=query.metric_id,
                    period=query.period,
                    value=42,
                ),
            ),
            citation_source_ids=(methodology.source_id,),
        )
    )
    runtime = GroundedStakeholderRagRuntime(
        policy=AudiencePolicyEngine(),
        metrics=FakeStakeholderMetricsAdapter((snapshot,)),
        methodology_source=source,
        methodology_retriever=retriever,
        provider=provider,
    )
    result = runtime.explain(
        principal=principal,
        query=query,
        question="Explica la metodología de usuarios activos",
        correlation_id="smoke-stakeholder-rag",
    )
    assert result.accepted
    assert result.claims[0].value == snapshot.value
    assert result.citations[0].source_id == methodology.source_id
    assert result.analytics_provenance == snapshot.provenance

    suppressed_runtime = GroundedStakeholderRagRuntime(
        policy=AudiencePolicyEngine(),
        metrics=FakeStakeholderMetricsAdapter(
            (snapshot.model_copy(update={"cohort_size": 9}),)
        ),
        methodology_source=FakeMethodologySource((methodology,)),
        methodology_retriever=FakeMethodologyRetriever(),
        provider=FakeStakeholderGroundedAnswerAdapter(
            StakeholderGroundedAnswer(
                narrative="No debe ejecutarse.",
                claims=(MetricClaim(metric_id=query.metric_id, period=query.period, value=1),),
                citation_source_ids=(methodology.source_id,),
            )
        ),
    )
    denied = suppressed_runtime.explain(
        principal=principal,
        query=query,
        question="Explica la métrica",
        correlation_id="smoke-stakeholder-rag-suppressed",
    )
    assert denied.accepted
    assert denied.code == "small_cohort_suppressed"
    assert denied.trace.provider_called is False

    return {
        "ok": True,
        "mode": "deterministic-fakes",
        "decision_code": result.code,
        "claim_count": len(result.claims),
        "citation_count": len(result.citations),
        "claim_matches_snapshot": True,
        "unknown_citation_forwarded": False,
        "suppressed_cohort_provider_call": False,
    }


def main() -> int:
    print(json.dumps(run_smoke(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
