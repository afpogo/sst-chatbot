from __future__ import annotations

from enum import Enum
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator


class Audience(str, Enum):
    SST_USER = "sst_user"
    SST_STAKEHOLDER = "sst_stakeholder"


class DataClassification(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"
    DERIVED_SAFE = "derived_safe"
    RESTRICTED = "restricted"
    SECRET = "secret"


class SafeContextSource(str, Enum):
    SST_BACKEND = "sst_backend"
    APPROVED_ANALYTICS = "approved_analytics"
    APPROVED_METHODOLOGY = "approved_methodology"


class PrincipalScope(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    application_id: str = Field(min_length=1)
    tenant_id: str = ""
    user_id: str = ""


class PrincipalContext(BaseModel):
    """Identity and authorization facts asserted exclusively by the SST backend."""

    model_config = {"extra": "forbid", "frozen": True}

    principal_id: str = Field(min_length=1)
    audience: Audience
    scope: PrincipalScope
    entitlements: frozenset[str] = Field(default_factory=frozenset)
    asserted_by: Literal["sst_backend"]
    authentication_ref: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_audience_scope(self) -> "PrincipalContext":
        if self.audience is Audience.SST_USER and (
            not self.scope.tenant_id or not self.scope.user_id
        ):
            raise ValueError("sst_user requires tenant_id and user_id")
        return self


class SafeContextEnvelope(BaseModel):
    """Context classified and scoped by an approved SST-owned source."""

    model_config = {"extra": "forbid", "frozen": True}

    envelope_id: str = Field(min_length=1)
    source: SafeContextSource
    classification: DataClassification
    scope: PrincipalScope
    payload: dict[str, Any]
    allowed_fields: tuple[str, ...] = Field(min_length=1)
    required_entitlements: frozenset[str] = Field(default_factory=frozenset)
    provenance: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_minimization_fields(self) -> "SafeContextEnvelope":
        missing = set(self.allowed_fields) - set(self.payload)
        if missing:
            raise ValueError(f"allowed_fields are absent from payload: {sorted(missing)}")
        return self


class ApprovedContext(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    envelope_id: str
    classification: DataClassification
    data: dict[str, Any]


class AccessDecision(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    allowed: bool
    code: str
    reason: str
    approved_context: tuple[ApprovedContext, ...] = ()


class DisclosureDecision(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    allowed: bool
    code: str
    reason: str


class MetricId(str, Enum):
    ACTIVE_ACCOUNTS = "active_accounts"
    ACTIVE_USERS = "active_users"
    NEW_ACCOUNTS = "new_accounts"
    RETENTION_RATE = "retention_rate"
    OPERATION_VOLUME = "operation_volume"
    MODULE_ADOPTION = "module_adoption"


class MetricQuery(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    metric_id: MetricId
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    granularity: Literal["monthly"] = "monthly"
    dimension: Literal["module_id"] | None = None
    dimension_value: str | None = None

    @model_validator(mode="after")
    def restrict_dimensions(self) -> "MetricQuery":
        if self.metric_id is MetricId.MODULE_ADOPTION:
            if self.dimension != "module_id" or not self.dimension_value:
                raise ValueError("module_adoption requires a module_id dimension")
        elif self.dimension is not None or self.dimension_value is not None:
            raise ValueError("dimensions are only supported for module_adoption")
        return self


MetricValue = int | float


class MetricSnapshot(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    metric_id: MetricId
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    granularity: Literal["monthly"] = "monthly"
    value: MetricValue | None
    definition: str = Field(min_length=1)
    cohort_size: int = Field(ge=0)
    suppressed: bool = False
    dimension: Literal["module_id"] | None = None
    dimension_value: str | None = None
    source: Literal["approved_analytics"] = "approved_analytics"
    provenance: str


class MethodologyRecord(BaseModel):
    """Owner-controlled methodology candidate; it never carries KPI values."""

    model_config = {"extra": "forbid", "frozen": True}

    source_id: str = Field(min_length=1)
    metric_id: MetricId
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    classification: DataClassification
    required_entitlements: frozenset[str] = Field(default_factory=frozenset)
    active: bool
    indexable: bool
    provenance: str = Field(min_length=1)


class AuthorizedMethodology(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    source_id: str
    title: str
    content: str
    provenance: str


class MethodologyCitation(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    source_id: str
    title: str
    provenance: str


class MetricClaim(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    metric_id: MetricId
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    value: MetricValue
    dimension: Literal["module_id"] | None = None
    dimension_value: str | None = None


class ProviderAnswer(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    text: str
    claims: tuple[MetricClaim, ...] = ()


class StakeholderGroundedAnswer(BaseModel):
    """Provider output keeps KPI values structured and narrative non-numeric."""

    model_config = {"extra": "forbid", "frozen": True}

    narrative: str = Field(min_length=1)
    claims: tuple[MetricClaim, ...] = Field(min_length=1)
    citation_source_ids: tuple[str, ...] = Field(min_length=1)


class StakeholderRagTrace(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    correlation_id: str = Field(min_length=1)
    decision_code: str = Field(min_length=1)
    methodology_candidate_count: int = Field(ge=0)
    methodology_authorized_count: int = Field(ge=0)
    methodology_retrieved_count: int = Field(ge=0)
    provider_called: bool
    contains_business_data: Literal[False] = False


class StakeholderRagResult(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    accepted: bool
    code: str
    snapshot: MetricSnapshot | None = None
    narrative: str = ""
    claims: tuple[MetricClaim, ...] = ()
    citations: tuple[MethodologyCitation, ...] = ()
    analytics_provenance: str = ""
    trace: StakeholderRagTrace
    handoff_required: Literal[False] = False


class PreparedProviderRequest(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    access_decision: AccessDecision
    provider_input: tuple[dict[str, str], ...] = ()
    trace_metadata: dict[str, Any] = Field(default_factory=dict)
    audit_metadata: dict[str, Any] = Field(default_factory=dict)
    handoff_required: Literal[False] = False


class AudienceReadResult(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    accepted: bool
    code: str
    snapshot: MetricSnapshot | None = None
    provider_request: PreparedProviderRequest | None = None
    handoff_required: Literal[False] = False
