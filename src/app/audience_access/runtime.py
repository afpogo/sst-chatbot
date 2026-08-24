from __future__ import annotations

from app.audience_access.contracts import Audience
from app.audience_access.contracts import AudienceReadResult
from app.audience_access.contracts import DataClassification
from app.audience_access.contracts import MetricQuery
from app.audience_access.contracts import MetricSnapshot
from app.audience_access.contracts import PrincipalContext
from app.audience_access.contracts import PrincipalScope
from app.audience_access.contracts import SafeContextEnvelope
from app.audience_access.contracts import SafeContextSource
from app.audience_access.metrics import MetricSourceUnavailable
from app.audience_access.metrics import StakeholderMetricsPort
from app.audience_access.policy import AudiencePolicyEngine
from app.audience_access.policy import MINIMUM_COHORT_SIZE
from app.audience_access.policy import STAKEHOLDER_ENTITLEMENT


class AudienceReadRuntime:
    """Read-only facade. It prepares model input and never creates a handoff."""

    def __init__(
        self,
        policy: AudiencePolicyEngine,
        metrics_port: StakeholderMetricsPort,
    ) -> None:
        self._policy = policy
        self._metrics_port = metrics_port

    def read_stakeholder_metric(
        self,
        principal: PrincipalContext,
        query: MetricQuery,
        *,
        user_message: str = "",
    ) -> AudienceReadResult:
        if principal.audience is not Audience.SST_STAKEHOLDER:
            return AudienceReadResult(accepted=False, code="audience_mismatch")
        if STAKEHOLDER_ENTITLEMENT not in principal.entitlements:
            return AudienceReadResult(accepted=False, code="missing_entitlement")
        try:
            snapshot = self._metrics_port.fetch_snapshot(query)
        except MetricSourceUnavailable:
            return AudienceReadResult(accepted=False, code="metric_source_unavailable")

        if not self._snapshot_matches_query(snapshot, query):
            return AudienceReadResult(accepted=False, code="snapshot_mismatch")
        if snapshot.source != SafeContextSource.APPROVED_ANALYTICS.value:
            return AudienceReadResult(accepted=False, code="unapproved_source")
        if not snapshot.provenance.strip():
            return AudienceReadResult(accepted=False, code="missing_provenance")

        if snapshot.cohort_size < MINIMUM_COHORT_SIZE:
            suppressed = snapshot.model_copy(
                update={"suppressed": True, "value": None}
            )
            return AudienceReadResult(
                accepted=True,
                code="small_cohort_suppressed",
                snapshot=suppressed,
            )
        if snapshot.suppressed or snapshot.value is None:
            return AudienceReadResult(
                accepted=True,
                code="source_suppressed",
                snapshot=snapshot.model_copy(update={"suppressed": True, "value": None}),
            )

        envelope = SafeContextEnvelope(
            envelope_id=f"metric:{query.metric_id.value}:{query.period}",
            source=SafeContextSource.APPROVED_ANALYTICS,
            classification=DataClassification.DERIVED_SAFE,
            scope=PrincipalScope(application_id=principal.scope.application_id),
            payload=snapshot.model_dump(mode="json"),
            allowed_fields=(
                "metric_id",
                "period",
                "granularity",
                "value",
                "definition",
                "cohort_size",
                "dimension",
                "dimension_value",
            ),
            required_entitlements=frozenset({STAKEHOLDER_ENTITLEMENT}),
            provenance=snapshot.provenance,
        )
        request = self._policy.prepare_provider_request(
            principal,
            user_message or f"Explain the approved {query.metric_id.value} snapshot.",
            (envelope,),
        )
        return AudienceReadResult(
            accepted=request.access_decision.allowed,
            code=request.access_decision.code,
            snapshot=snapshot,
            provider_request=request,
        )

    @staticmethod
    def _snapshot_matches_query(
        snapshot: MetricSnapshot,
        query: MetricQuery,
    ) -> bool:
        return (
            snapshot.metric_id == query.metric_id
            and snapshot.period == query.period
            and snapshot.granularity == query.granularity
            and snapshot.dimension == query.dimension
            and snapshot.dimension_value == query.dimension_value
        )
