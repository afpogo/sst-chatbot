"""One-shot provider boundary, without finalization, retries or persistence."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal, Protocol

from pydantic import Field, ValidationError

from app.article_processing.contracts import AnalysisContent, AnalysisRequest, ContractValue
from app.article_processing.prompts import CompositionError, CompositionLimits, compose_article_prompt


class ProviderBoundaryError(ValueError):
    """Fixed failure codes only, never private provider details."""


@dataclass(frozen=True)
class ProviderMessage:
    role: Literal["system", "human", "assistant"]
    content: str = field(repr=False)


@dataclass(frozen=True)
class ProviderReply:
    status: Literal["completed", "truncated", "refused"]
    text: str = field(repr=False)


class ArticleProvider(Protocol):
    def complete(self, messages: tuple[ProviderMessage, ...], *,
                 max_output_tokens: int, timeout_seconds: int) -> ProviderReply:
        """Adapters enforce timeout/output cap and must not log message bodies."""
        ...


class ProviderLimits(ContractValue):
    max_response_bytes: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)
    timeout_seconds: int = Field(gt=0)


@dataclass(frozen=True)
class ValidatedAnalysis:
    content: AnalysisContent = field(repr=False)
    prompt_hash: str


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError("nonfinite_json")


def parse_analysis_reply(text: str, *, max_response_bytes: int) -> AnalysisContent:
    """Parse one exact JSON object, without repair or value coercion."""
    if type(max_response_bytes) is not int or max_response_bytes <= 0:
        raise ProviderBoundaryError("invalid_response_limit")
    if not isinstance(text, str):
        raise ProviderBoundaryError("invalid_provider_output")
    try:
        size = len(text.encode("utf-8"))
    except UnicodeError:
        raise ProviderBoundaryError("invalid_provider_output") from None
    if size > max_response_bytes:
        raise ProviderBoundaryError("provider_output_limit")
    try:
        payload = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        required = {"schema_version", "evidence", "inferences", "uncertainties", "open_questions", "synthesis"}
        if not isinstance(payload, dict) or set(payload) != required:
            raise ValueError("invalid_fields")
        for key in ("evidence", "inferences", "uncertainties", "open_questions"):
            if type(payload[key]) is not list:
                raise ValueError("invalid_array")
            if any(type(item) is not str or not item.strip() for item in payload[key]):
                raise ValueError("invalid_array_item")
            payload[key] = tuple(payload[key])
        if type(payload["synthesis"]) is not str or not payload["synthesis"].strip():
            raise ValueError("invalid_synthesis")
        return AnalysisContent.model_validate(payload)
    except (ValueError, TypeError, RecursionError):
        raise ProviderBoundaryError("invalid_provider_output") from None


def analyze_once(
    request: AnalysisRequest, *, provider: ArticleProvider,
    composition_limits: CompositionLimits, provider_limits: ProviderLimits,
    paragraph_ordinal: int | None = None, bounded_context: str = "",
) -> ValidatedAnalysis:
    """One validated call is not a completed run or persisted result."""
    try:
        limits = ProviderLimits.model_validate(provider_limits)
    except ValidationError:
        raise ProviderBoundaryError("invalid_provider_limits") from None
    try:
        rendered = compose_article_prompt(
            request, limits=composition_limits, paragraph_ordinal=paragraph_ordinal,
            bounded_context=bounded_context,
        )
    except (CompositionError, UnicodeError):
        raise ProviderBoundaryError("invalid_analysis_input") from None
    return analyze_rendered(rendered, provider=provider, provider_limits=limits)


def analyze_rendered(rendered, *, provider: ArticleProvider,
                     provider_limits: ProviderLimits) -> ValidatedAnalysis:
    """Internal trusted-composer boundary; never accept caller-supplied messages."""
    try:
        limits = ProviderLimits.model_validate(provider_limits)
    except ValidationError:
        raise ProviderBoundaryError("invalid_provider_limits") from None
    messages = tuple(ProviderMessage(m.role, m.content) for m in rendered.messages)
    try:
        reply = provider.complete(messages, max_output_tokens=limits.max_output_tokens,
                                  timeout_seconds=limits.timeout_seconds)
    except TimeoutError:
        raise ProviderBoundaryError("provider_timeout") from None
    except Exception:
        # No exception text, body logging or automatic retry across this boundary.
        raise ProviderBoundaryError("provider_failure") from None
    if not isinstance(reply, ProviderReply):
        raise ProviderBoundaryError("invalid_provider_reply")
    if reply.status == "truncated":
        raise ProviderBoundaryError("provider_truncated")
    if reply.status == "refused":
        raise ProviderBoundaryError("provider_refused")
    if reply.status != "completed":
        raise ProviderBoundaryError("invalid_provider_reply")
    content = parse_analysis_reply(reply.text, max_response_bytes=limits.max_response_bytes)
    return ValidatedAnalysis(content, rendered.trace_metadata.prompt_hash)
