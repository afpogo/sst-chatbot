from __future__ import annotations

from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import Field

PromptRole = Literal["system", "human", "assistant"]
PromptStatus = Literal["draft", "stable", "deprecated"]
PromptTracePolicy = Literal["metadata_only"]
PromptVisibility = Literal["internal_private"]
PromptProviderCachePolicy = Literal["none", "in_memory", "24h"]
PromptVariableType = Literal["string", "integer", "number", "boolean", "list", "object"]


class PromptVariable(BaseModel):
    name: str
    type: PromptVariableType = "string"
    required: bool = True
    default: Any = None
    sensitive: bool = False
    description: str = ""


class PromptMessage(BaseModel):
    role: PromptRole
    template: str


class PromptDefinition(BaseModel):
    id: str
    version: str
    status: PromptStatus = "draft"
    description: str = ""
    messages: tuple[PromptMessage, ...]
    variables: tuple[PromptVariable, ...] = ()
    tags: tuple[str, ...] = ()
    visibility: PromptVisibility = "internal_private"
    trace_policy: PromptTracePolicy = "metadata_only"
    provider_cache_policy: PromptProviderCachePolicy = "none"
    compatible_providers: tuple[str, ...] = ("any",)
    compatible_models: tuple[str, ...] = ("any",)


class RenderedPromptMessage(BaseModel):
    role: PromptRole
    content: str


class PromptTraceMetadata(BaseModel):
    prompt_id: str
    prompt_version: str
    prompt_hash: str
    provider: str = ""
    model: str = ""
    trace_policy: PromptTracePolicy = "metadata_only"
    provider_cache_policy: PromptProviderCachePolicy = "none"
    visibility: PromptVisibility = "internal_private"
    variable_names: tuple[str, ...] = ()
    render_ms: float = 0.0


class PromptRenderRequest(BaseModel):
    prompt_id: str
    version: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    provider: str = ""
    model: str = ""


class PromptRenderResult(BaseModel):
    prompt: PromptDefinition
    messages: tuple[RenderedPromptMessage, ...]
    trace_metadata: PromptTraceMetadata
