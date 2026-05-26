# ADR 0002: Provider, Model, And Memory Configuration

## Status
Accepted.

## Context
The project needs to swap model providers and memory behavior without rewriting agent code. OpenAI is the first concrete provider, but the repo must remain provider-agnostic for Anthropic, Deepseek, local models, GitHub Copilot-like coding models, or future providers.

OpenAI's current guidance favors the Responses API for reasoning, tool use, and multi-turn state. The relevant parameters for future agent work include:
- `reasoning.effort` for GPT-5 family reasoning models.
- `text.verbosity` for response length control.
- `previous_response_id` and Conversations API for stateful turns.
- `prompt_cache_retention` with allowed values `in_memory` and `24h`.

Sources:
- https://developers.openai.com/api/docs/models
- https://developers.openai.com/api/docs/guides/latest-model
- https://developers.openai.com/api/docs/guides/conversation-state
- https://developers.openai.com/api/docs/guides/prompt-caching

## Decision
Create provider-owned modules under `src/app/providers/`:
- `types.py`: shared Pydantic contracts for agent runtime, memory, and model profile configuration.
- `model_registry.py`: current known model profiles and capability flags.
- `openai_provider.py`: OpenAI adapter helpers and Responses API option derivation.
- `anthropic_provider.py`: reserved adapter boundary.
- `github_copilot_provider.py`: reserved adapter boundary.
- `factory.py`: provider switch for LangChain chat model construction.

Configuration is driven by environment variables through `src/app/config/settings.py`, not by hard-coded business logic.

## Consequences
- Agent code can request a provider/model/memory configuration without knowing the SDK implementation.
- OpenAI can use current model-specific knobs while other providers remain explicitly unsupported until dependencies and API contracts are declared.
- Memory is modeled separately from model choice so local, LangGraph, OpenAI Responses, OpenAI Conversations, and vector-store strategies can be selected independently.
- The repo avoids pretending GitHub Copilot or Anthropic are available until a supported API/dependency is added.

## Out Of Scope
- Production agents.
- Real provider calls in unit tests.
- LangGraph checkpoint implementation.
- Vector store persistence.
- Anthropic, Deepseek, GitHub Copilot, or local model SDK installation.

## Validation
Run:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts\ards_check.py
.\.venv\Scripts\python.exe scripts\check.py
```
