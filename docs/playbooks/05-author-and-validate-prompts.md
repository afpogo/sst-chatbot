# Playbook 05: Author And Validate Prompts

## Objective
Add or update a private SST prompt without scattering prompt text through agent code or exposing it through LangSmith-owned prompt storage.

## Preconditions
- Work from the repository root.
- Keep prompt bodies in `src/app/prompts/catalog/`.
- Use `metadata_only` trace policy.
- Use `internal_private` visibility.
- Use `provider_cache_policy: none` unless a future review explicitly allows cache retention.
- Add or update tests for behavior changes.

## Commands
Create or update a prompt YAML file under:

```text
src/app/prompts/catalog/
```

Register the prompt path in `src/app/prompts/registry.py`.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_prompt_engine.py
.\.venv\Scripts\python.exe scripts\ards_check.py
```

## Expected Result
The prompt loads through the registry, validates declared variables, renders with local inputs, and emits metadata-only trace information.

## Common Problems
- A placeholder like `{tenant_id}` must have a matching variable declaration.
- Render inputs with undeclared keys are rejected.
- Prompt YAML must use roles `system`, `human`, or `assistant`.
- Literal JSON braces must be escaped as `{{` and `}}`.
- Do not put provider API options or memory retrieval rules inside prompt YAML.

## Success Validation
```powershell
.\.venv\Scripts\python.exe scripts\check.py
```
