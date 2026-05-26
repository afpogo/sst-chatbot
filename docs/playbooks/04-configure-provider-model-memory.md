# Playbook 04: Configure Provider, Model, And Memory

## Objective
Change provider, model, reasoning, verbosity, and memory behavior by parameters.

## Preconditions
- Dependencies are installed.
- `.env` exists locally.
- Only OpenAI is currently implemented as a real LangChain provider adapter.

## Commands
Open `.env` and set the desired values:

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.4-mini
LLM_REASONING_EFFORT=medium
LLM_TEXT_VERBOSITY=medium
OPENAI_PROMPT_CACHE_RETENTION=auto
MEMORY_BACKEND=none
MEMORY_STRATEGY=stateless
```

For OpenAI Responses state chaining in a future manual integration:

```env
MEMORY_BACKEND=openai_responses
MEMORY_STRATEGY=previous_response
MEMORY_STORE_PROVIDER_STATE=true
OPENAI_PREVIOUS_RESPONSE_ID=resp_xxx
```

For OpenAI Conversations in a future manual integration:

```env
MEMORY_BACKEND=openai_conversations
MEMORY_STRATEGY=conversation
OPENAI_CONVERSATION_ID=conv_xxx
```

## Expected Result
`load_settings()` returns an `AgentRuntimeConfig` with provider, model, model parameters, and memory configuration populated from `.env`.

## Common Problems
- Setting `LLM_PROVIDER=anthropic` will not create a client yet; the adapter boundary exists but the dependency is not declared.
- Setting `LLM_PROVIDER=github_copilot` will not create a client yet; a supported API boundary must be defined first.
- Unit tests should not require real provider credentials.
- Unknown model names are allowed as custom models but no special capabilities are assumed.

## Success Validation
```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_settings.py tests\test_provider_configuration.py
```
