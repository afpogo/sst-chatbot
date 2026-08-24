from __future__ import annotations

import json
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, model_validator

from app.governed_rag.contracts import Citation
from app.governed_rag.policy import contains_credential_like_text


class UserMemoryPortError(RuntimeError):
    """A governed memory port failed without exposing its response body."""


class MemoryVisibility(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    user_visible: bool = True
    indexable: bool = True
    downloadable: bool = False
    provider_eligible: bool = True


class MemoryTags(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    domain: str = Field(min_length=1, max_length=80)
    topic: str = Field(min_length=1, max_length=80)
    kind: str = Field(min_length=1, max_length=80)
    source: str = Field(min_length=1, max_length=80)
    visibility: str = Field(min_length=1, max_length=80)
    lifecycle: str = Field(min_length=1, max_length=80)


class MemoryProposalCandidate(BaseModel):
    """Provider-agnostic candidate; Bend assigns evidence, producer and status."""

    model_config = {"extra": "forbid", "frozen": True}

    kind: Literal["fact", "intention", "thread"]
    content: dict[str, Any]
    confidence: float = Field(ge=0, le=1)
    validation_summary: dict[str, Any]
    tags: MemoryTags
    visibility: MemoryVisibility = Field(default_factory=MemoryVisibility)
    classification: Literal["public", "internal", "private"] = "private"

    @model_validator(mode="after")
    def validate_safe_structured_candidate(self) -> "MemoryProposalCandidate":
        required = {
            "fact": "statement",
            "intention": "intentText",
            "thread": "title",
        }[self.kind]
        if not isinstance(self.content.get(required), str) or not self.content[required].strip():
            raise ValueError(f"memory {self.kind} requires {required}")
        serialized = json.dumps(
            {"content": self.content, "validation_summary": self.validation_summary},
            sort_keys=True,
        )
        if contains_credential_like_text(serialized):
            raise ValueError("credential-like memory candidate is forbidden")
        forbidden = {
            "prompt",
            "renderedprompt",
            "systemprompt",
            "providerresponse",
            "llmresponse",
            "langchainmessages",
            "messages",
            "accesstoken",
            "refreshtoken",
        }

        def visit(value: Any) -> None:
            if isinstance(value, list):
                for item in value:
                    visit(item)
            elif isinstance(value, dict):
                for key, nested in value.items():
                    normalized = "".join(character for character in key.lower() if character.isalnum())
                    if normalized in forbidden:
                        raise ValueError("runtime or provider trace fields are forbidden")
                    visit(nested)

        visit(self.validation_summary)
        return self

    def bend_payload(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "content": self.content,
            "confidence": self.confidence,
            "validationSummary": self.validation_summary,
            "tags": self.tags.model_dump(mode="json"),
            "visibility": {
                "userVisible": self.visibility.user_visible,
                "indexable": self.visibility.indexable,
                "downloadable": self.visibility.downloadable,
                "providerEligible": self.visibility.provider_eligible,
            },
            "classification": self.classification,
        }


class MemoryProposalReceipt(BaseModel):
    model_config = {"extra": "ignore", "frozen": True}

    id: str = Field(min_length=1)
    status: Literal["needs_user_review"]


class MemoryProposalBuilderPort(Protocol):
    def build_candidate(
        self,
        *,
        question: str,
        answer: str,
        citations: tuple[Citation, ...],
        correlation_id: str,
    ) -> MemoryProposalCandidate | None:
        """Return an optional structured candidate, never canonical memory."""
