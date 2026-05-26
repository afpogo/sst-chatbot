# ADR 0003: Private Prompt Engine

## Status
Accepted.

## Context
SST agents need reusable prompts, but prompt bodies should not be scattered through Python modules or owned by LangSmith. The repository must keep prompts private, versioned, validated, and usable across providers.

## Decision
Create a repo-owned prompt engine under `src/app/prompts/`.

Prompts are YAML files in a private local catalog for V1. The engine loads only explicitly registered prompts, validates declared variables, renders messages locally, and emits trace metadata with `prompt_id`, `prompt_version`, `prompt_hash`, `provider`, `model`, variable names, visibility, and provider cache policy.

LangSmith must not be the source of prompts. The default trace policy is `metadata_only`, which prevents prompt body content from being intentionally added to prompt trace metadata.

Provider cache retention is a separate policy from LangSmith tracing. Internal private prompts default to `provider_cache_policy: none` so OpenAI prompt cache retention is not promoted to persistent retention by default when prompt metadata is passed to provider option builders.

## Consequences
- Prompts become versioned source artifacts.
- Agents can resolve prompts by `id` and `version`.
- Providers receive rendered messages, not prompt YAML.
- Future storage can move to a private registry service without changing agent code.
- Prompt changes become behavior changes that require tests and ARDS/SDD documentation.

## Out Of Scope
- Runtime prompt editing.
- Remote prompt registry service.
- Jinja2 or arbitrary template logic.
- A/B testing, canary rollout, or prompt admin UI.
- Migrating all existing POC inline prompts.

## Validation
Run:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts\ards_check.py
.\.venv\Scripts\python.exe scripts\check.py
```
