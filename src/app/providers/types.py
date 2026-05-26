from __future__ import annotations

from typing import Literal

from pydantic import BaseModel
from pydantic import Field

ProviderName = Literal["openai", "anthropic", "github_copilot", "deepseek", "local"]
ReasoningEffort = Literal["none", "low", "medium", "high", "xhigh"]
TextVerbosity = Literal["low", "medium", "high"]
PromptCacheRetention = Literal["auto", "in_memory", "24h"]
MemoryBackend = Literal[
    "none",
    "local",
    "langgraph_checkpoint",
    "openai_responses",
    "openai_conversations",
    "vector_store",
]
MemoryStrategy = Literal[
    "stateless",
    "window",
    "summary",
    "retrieval",
    "previous_response",
    "conversation",
]


class MemoryConfig(BaseModel):
    backend: MemoryBackend = "none"
    strategy: MemoryStrategy = "stateless"
    max_messages: int = 20
    max_tokens: int | None = None
    store_provider_state: bool = False
    conversation_id: str = ""
    previous_response_id: str = ""


class AgentRuntimeConfig(BaseModel):
    provider: ProviderName = "openai"
    model: str = "gpt-5.4-mini"
    temperature: float | None = None
    max_output_tokens: int | None = None
    reasoning_effort: ReasoningEffort = "medium"
    text_verbosity: TextVerbosity = "medium"
    prompt_cache_retention: PromptCacheRetention = "auto"
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    enable_tools: bool = True
    structured_outputs: bool = True


class ModelProfile(BaseModel):
    provider: ProviderName
    model: str
    family: str
    recommended_for: tuple[str, ...] = ()
    supports_reasoning_effort: bool = False
    supported_reasoning_efforts: tuple[ReasoningEffort, ...] = ()
    default_reasoning_effort: ReasoningEffort | None = None
    supports_text_verbosity: bool = False
    supports_prompt_cache_retention: bool = False
    default_prompt_cache_retention: PromptCacheRetention = "auto"
    supports_previous_response_id: bool = False
    supports_conversations_api: bool = False
    context_window_tokens: int | None = None
    max_output_tokens: int | None = None
    source_url: str = ""
    notes: str = ""
