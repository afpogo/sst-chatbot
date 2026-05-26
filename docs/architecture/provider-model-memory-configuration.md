# Provider, Model, And Memory Configuration

## Intent
This architecture lets future agents swap providers, models, and memory behavior by parameters instead of code rewrites.

The goal is a stable repo-owned contract:
- provider selection;
- model selection;
- model capability profile;
- reasoning and verbosity knobs;
- memory backend and strategy;
- provider-specific request options.

## Code Structure
- `src/app/providers/types.py`: Pydantic contracts.
- `src/app/providers/model_registry.py`: known model capabilities.
- `src/app/providers/openai_provider.py`: OpenAI adapter and Responses API option derivation.
- `src/app/providers/factory.py`: provider switch for LangChain chat model construction.
- `src/app/config/settings.py`: `.env` loading and config assembly.

## OpenAI Model Notes
Current OpenAI docs list GPT-5.5, GPT-5.4, and GPT-5.4 mini as frontier models for coding and agentic workloads. GPT-5.5 is documented as the current strongest model for complex production workflows, while GPT-5.4 mini is better aligned with lower-cost local development and well-defined tasks.

The registry captures only a small set of model capabilities needed by this repo. Unknown models resolve to a custom profile with no assumed capabilities.

Sources:
- https://developers.openai.com/api/docs/models
- https://developers.openai.com/api/docs/guides/latest-model

## Memory Options
Memory is not one thing. The repo separates memory into backend and strategy:
- `none` + `stateless`: no memory.
- `local` + `window`: local rolling message window.
- `local` + `summary`: future local summary memory.
- `langgraph_checkpoint`: future LangGraph checkpointing.
- `openai_responses` + `previous_response`: use OpenAI `previous_response_id`.
- `openai_conversations` + `conversation`: use OpenAI Conversations API.
- `vector_store` + `retrieval`: future RAG-backed memory.

OpenAI response objects are saved for 30 days by default, and `store=false` disables response storage. Conversation objects are durable and not subject to that 30-day TTL. This repo exposes `MEMORY_STORE_PROVIDER_STATE` so persistence is explicit.

Sources:
- https://developers.openai.com/api/docs/guides/conversation-state

## Prompt Cache Options
OpenAI prompt caching can be configured with `prompt_cache_retention`. Current documented values are `in_memory` and `24h`. GPT-5.5 defaults to `24h`; most older supported models default to `in_memory`.

Source:
- https://developers.openai.com/api/docs/guides/prompt-caching

## Provider Boundaries
OpenAI is implemented because `langchain-openai` is declared.

Anthropic, GitHub Copilot, Deepseek, and local models are represented as configuration/provider names, but they are not enabled until the repo declares dependencies and an adapter contract. This is deliberate: provider swap must be explicit, testable, and documented.
