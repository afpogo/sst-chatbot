from __future__ import annotations

import re

from app.audience_access.contracts import AuthorizedMethodology
from app.audience_access.contracts import DataClassification
from app.audience_access.contracts import MethodologyCitation
from app.audience_access.contracts import MethodologyRecord
from app.audience_access.contracts import MetricClaim
from app.audience_access.contracts import MetricQuery
from app.audience_access.contracts import MetricSnapshot
from app.audience_access.contracts import PrincipalContext
from app.audience_access.contracts import PrincipalScope
from app.audience_access.contracts import ProviderAnswer
from app.audience_access.contracts import SafeContextEnvelope
from app.audience_access.contracts import SafeContextSource
from app.audience_access.contracts import StakeholderRagResult
from app.audience_access.contracts import StakeholderRagTrace
from app.audience_access.methodology import MethodologyRetrieverPort
from app.audience_access.methodology import StakeholderGroundedAnswerPort
from app.audience_access.methodology import StakeholderMethodologySourcePort
from app.audience_access.metrics import StakeholderMetricsPort
from app.audience_access.policy import AudiencePolicyEngine
from app.audience_access.runtime import AudienceReadRuntime


_NUMERIC_NARRATIVE = re.compile(r"(?<![A-Za-z0-9_])[-+]?\d+(?:[.,]\d+)?%?")


class GroundedStakeholderRagRuntime:
    """Compose approved KPI values with cited methodology and no handoff."""

    def __init__(
        self,
        *,
        policy: AudiencePolicyEngine,
        metrics: StakeholderMetricsPort,
        methodology_source: StakeholderMethodologySourcePort,
        methodology_retriever: MethodologyRetrieverPort,
        provider: StakeholderGroundedAnswerPort,
        methodology_limit: int = 3,
    ) -> None:
        if methodology_limit <= 0:
            raise ValueError("methodology_limit must be greater than zero")
        self._policy = policy
        self._metric_runtime = AudienceReadRuntime(policy, metrics)
        self._methodology_source = methodology_source
        self._methodology_retriever = methodology_retriever
        self._provider = provider
        self._methodology_limit = methodology_limit

    def explain(
        self,
        *,
        principal: PrincipalContext,
        query: MetricQuery,
        question: str,
        correlation_id: str,
    ) -> StakeholderRagResult:
        if not correlation_id.strip():
            raise ValueError("correlation_id is required")
        metric_result = self._metric_runtime.read_stakeholder_metric(
            principal,
            query,
            user_message=question,
        )
        if not metric_result.accepted or metric_result.provider_request is None:
            return self._result(
                metric_result.accepted,
                metric_result.code,
                correlation_id,
                snapshot=metric_result.snapshot,
            )
        snapshot = metric_result.snapshot
        if snapshot is None:
            return self._result(False, "missing_snapshot", correlation_id)

        try:
            candidates = tuple(self._methodology_source.list_candidates(query))
        except Exception:
            return self._result(
                False,
                "methodology_source_error",
                correlation_id,
                snapshot=snapshot,
            )

        try:
            authorized = tuple(
                item
                for record in candidates
                if (item := self._authorize_methodology(principal, query, record))
                is not None
            )
        except Exception:
            return self._result(
                False,
                "methodology_policy_error",
                correlation_id,
                snapshot=snapshot,
                candidate_count=len(candidates),
            )
        if not authorized:
            return self._result(
                False,
                "no_authorized_methodology",
                correlation_id,
                snapshot=snapshot,
                candidate_count=len(candidates),
            )

        try:
            retrieved = self._methodology_retriever.retrieve(
                question=question,
                methodology=authorized,
                limit=self._methodology_limit,
            )
        except Exception:
            return self._result(
                False,
                "methodology_retriever_error",
                correlation_id,
                snapshot=snapshot,
                candidate_count=len(candidates),
                authorized_count=len(authorized),
            )
        if not retrieved:
            return self._result(
                False,
                "insufficient_methodology",
                correlation_id,
                snapshot=snapshot,
                candidate_count=len(candidates),
                authorized_count=len(authorized),
            )

        try:
            answer = self._provider.answer(
                question=question,
                snapshot=snapshot,
                methodology=retrieved,
                correlation_id=correlation_id,
            )
            if _NUMERIC_NARRATIVE.search(answer.narrative):
                return self._result(
                    False,
                    "numeric_narrative_forbidden",
                    correlation_id,
                    snapshot=snapshot,
                    candidate_count=len(candidates),
                    authorized_count=len(authorized),
                    retrieved_count=len(retrieved),
                    provider_called=True,
                )
            disclosure = self._policy.validate_disclosure(
                ProviderAnswer(text=answer.narrative, claims=answer.claims),
                (snapshot,),
            )
        except Exception:
            return self._result(
                False,
                "provider_error",
                correlation_id,
                snapshot=snapshot,
                candidate_count=len(candidates),
                authorized_count=len(authorized),
                retrieved_count=len(retrieved),
                provider_called=True,
            )
        if not disclosure.allowed:
            return self._result(
                False,
                disclosure.code,
                correlation_id,
                snapshot=snapshot,
                candidate_count=len(candidates),
                authorized_count=len(authorized),
                retrieved_count=len(retrieved),
                provider_called=True,
            )

        by_id = {item.source_id: item for item in retrieved}
        citation_ids = tuple(dict.fromkeys(answer.citation_source_ids))
        if not citation_ids or not set(citation_ids).issubset(by_id):
            return self._result(
                False,
                "unknown_methodology_citation",
                correlation_id,
                snapshot=snapshot,
                candidate_count=len(candidates),
                authorized_count=len(authorized),
                retrieved_count=len(retrieved),
                provider_called=True,
            )
        citations = tuple(
            MethodologyCitation(
                source_id=by_id[source_id].source_id,
                title=by_id[source_id].title,
                provenance=by_id[source_id].provenance,
            )
            for source_id in citation_ids
        )
        return self._result(
            True,
            "grounded_stakeholder_answer",
            correlation_id,
            snapshot=snapshot,
            narrative=answer.narrative,
            claims=answer.claims,
            citations=citations,
            analytics_provenance=snapshot.provenance,
            candidate_count=len(candidates),
            authorized_count=len(authorized),
            retrieved_count=len(retrieved),
            provider_called=True,
        )

    def _authorize_methodology(
        self,
        principal: PrincipalContext,
        query: MetricQuery,
        record: MethodologyRecord,
    ) -> AuthorizedMethodology | None:
        if not isinstance(record, MethodologyRecord):
            raise TypeError("methodology record has an invalid type")
        if (
            record.metric_id != query.metric_id
            or not record.active
            or not record.indexable
            or record.classification
            not in {DataClassification.PUBLIC, DataClassification.DERIVED_SAFE}
        ):
            return None
        envelope = SafeContextEnvelope(
            envelope_id=f"methodology:{record.source_id}",
            source=SafeContextSource.APPROVED_METHODOLOGY,
            classification=record.classification,
            scope=PrincipalScope(application_id=principal.scope.application_id),
            payload={"title": record.title, "content": record.content},
            allowed_fields=("title", "content"),
            required_entitlements=record.required_entitlements,
            provenance=record.provenance,
        )
        decision = self._policy.authorize_context(principal, (envelope,))
        if not decision.allowed:
            return None
        return AuthorizedMethodology(
            source_id=record.source_id,
            title=record.title,
            content=record.content,
            provenance=record.provenance,
        )

    @staticmethod
    def _result(
        accepted: bool,
        code: str,
        correlation_id: str,
        *,
        snapshot: MetricSnapshot | None = None,
        narrative: str = "",
        claims: tuple[MetricClaim, ...] = (),
        citations: tuple[MethodologyCitation, ...] = (),
        analytics_provenance: str = "",
        candidate_count: int = 0,
        authorized_count: int = 0,
        retrieved_count: int = 0,
        provider_called: bool = False,
    ) -> StakeholderRagResult:
        return StakeholderRagResult(
            accepted=accepted,
            code=code,
            snapshot=snapshot,
            narrative=narrative,
            claims=claims,
            citations=citations,
            analytics_provenance=analytics_provenance,
            trace=StakeholderRagTrace(
                correlation_id=correlation_id,
                decision_code=code,
                methodology_candidate_count=candidate_count,
                methodology_authorized_count=authorized_count,
                methodology_retrieved_count=retrieved_count,
                provider_called=provider_called,
            ),
        )
