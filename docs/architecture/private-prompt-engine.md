# Private Prompt Engine

## Intent
The private prompt engine centralizes SST core prompts so they are not scattered across agent code, notebooks, or LangSmith. It provides deterministic prompt resolution, strict variable validation, local rendering, and safe trace metadata.

## Runtime Flow
```text
agent or graph node
  -> prompt registry resolves prompt_id/version
  -> renderer validates variables and applies defaults
  -> renderer emits messages and metadata_only trace metadata
  -> assembler converts messages for LangChain
  -> provider adapter receives rendered messages
```

## V1 Design
- Prompt catalog lives under `src/app/prompts/catalog/`.
- `registry.py` loads a fixed allowlist of YAML prompt files.
- `renderer.py` supports `{variable}` replacement only.
- `validators.py` rejects missing variables, undeclared variables, invalid types, invalid roles, undeclared placeholders, attribute/index placeholders, format specs, and conversions.
- `assembler.py` converts rendered messages to LangChain message objects.
- Prompt trace metadata never includes rendered prompt bodies or variable values.
- Provider prompt-cache policy is separate from tracing policy. Internal private prompts default to `provider_cache_policy: none`.

## Prompt Contract
Every catalog prompt must define:
- `id`
- `version`
- `status`
- `description`
- `messages`
- `variables`
- `trace_policy`
- `visibility`
- `provider_cache_policy`
- `compatible_providers`
- `compatible_models`

V1 roles are `system`, `human`, and `assistant`. V1 trace policy is `metadata_only`. V1 visibility is `internal_private`.

## Boundaries
- Prompt config is not provider config.
- Prompt YAML does not own memory retrieval or provider calls.
- `src/app/memory` prepares context variables.
- `src/app/providers` receives rendered messages.
- LangSmith may receive prompt metadata, but not prompt bodies through this engine.

## Future Direction
V2 can introduce a private prompt registry service, approval workflows, rollout labels, evaluation datasets, and tenant-specific prompt storage. The V1 interfaces are intentionally storage-agnostic so this can happen without changing agent code.
