from __future__ import annotations

from enum import Enum

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator

from app.audience_access.contracts import DataClassification


class RagStatus(str, Enum):
    COMPLETED = "completed"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    DENIED = "denied"
    ERROR = "error"


class RetrievalScope(BaseModel):
    """Scope derived from an SST-validated principal, never from user text."""

    model_config = {"extra": "forbid", "frozen": True}

    tenant_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    application_id: str = Field(min_length=1)
    entitlements: frozenset[str] = Field(default_factory=frozenset)
    allowed_classifications: frozenset[DataClassification] = Field(min_length=1)
    allowed_sources: frozenset[str] = Field(min_length=1)
    policy_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def reject_prohibited_classifications(self) -> "RetrievalScope":
        prohibited = {
            DataClassification.RESTRICTED,
            DataClassification.SECRET,
        }
        if self.allowed_classifications.intersection(prohibited):
            raise ValueError("restricted and secret classifications cannot be allowed")
        return self


class GovernedMemoryRecord(BaseModel):
    """Candidate record returned by a governed source before local policy."""

    model_config = {"extra": "forbid", "frozen": True}

    record_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    application_id: str = Field(min_length=1)
    classification: DataClassification
    required_entitlements: frozenset[str] = Field(default_factory=frozenset)
    active: bool
    indexable: bool
    provenance: str = Field(min_length=1)


class AuthorizedChunk(BaseModel):
    """Projection allowed to cross the policy-to-retriever boundary."""

    model_config = {"extra": "forbid", "frozen": True}

    chunk_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    provenance: str = Field(min_length=1)


class RankedChunk(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    chunk: AuthorizedChunk
    score: float = Field(gt=0)


class ProviderContext(BaseModel):
    """Minimal context supplied to a provider adapter."""

    model_config = {"extra": "forbid", "frozen": True}

    chunk_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class GroundedClaim(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    text: str = Field(min_length=1)
    citation_chunk_ids: tuple[str, ...] = Field(min_length=1)


class GroundedAnswer(BaseModel):
    """Structured provider output; free-form uncited answer text is forbidden."""

    model_config = {"extra": "forbid", "frozen": True}

    claims: tuple[GroundedClaim, ...] = Field(min_length=1)


class Citation(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    chunk_id: str
    source_id: str
    title: str
    provenance: str


class DecisionTrace(BaseModel):
    """Metadata-only trace safe for logs and central evidence."""

    model_config = {"extra": "forbid", "frozen": True}

    correlation_id: str = Field(min_length=1)
    decision_code: str = Field(min_length=1)
    candidate_count: int = Field(ge=0)
    authorized_count: int = Field(ge=0)
    retrieved_count: int = Field(ge=0)
    contains_business_data: bool = False


class RagResult(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    status: RagStatus
    decision_code: str
    answer: str = ""
    citations: tuple[Citation, ...] = ()
    trace: DecisionTrace
