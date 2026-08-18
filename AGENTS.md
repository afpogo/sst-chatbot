# Repository Guidelines

## Project Purpose
This repository is the AI agent experimentation and integration base for SST and future applications.

The long-term design is provider-agnostic: OpenAI, Anthropic, Deepseek, local models, or future providers should be replaceable behind repo-owned contracts.

The product intent is to evolve this repository into a governed agent runtime core for SST: operational context becomes governed memory, private prompts, provider-agnostic model calls, structured validated intents, and orchestrator handoffs.

## ARDS/SDD Operating Model
- `AGENTS.md`: operational guide for humans and AI agents.
- `docs/`: human-readable context, architecture, ADRs, POC policy, and task notes.
- `specs/`: structured source of truth for capabilities, integrations, POCs, and future state scenarios.
- `labs/`: notebooks and experiments that are not yet production contracts.
- `pocs/`: legacy POC policy and POC-related context; durable POC contracts live in `specs/pocs/`.
- `src/`: reusable implementation promoted from POCs.
- `tests/`: automated validation.

## Project Structure
- `init.py`: validates environment loading and OpenAI/LangChain imports.
- `src/app/`: primary maintainable application package for future agents.
- `src/app/config/settings.py`: environment and runtime configuration helpers for the new app base.
- `src/app/llm/openai_client.py`: future OpenAI/LangChain client initialization boundary.
- `src/app/providers/`: provider, model, and memory configuration contracts plus provider adapters.
- `src/app/prompts/`: private prompt catalog, validation, rendering, and LangChain assembly helpers.
- `src/sst_chatbot/config.py`: environment and runtime configuration helpers.
- `src/sst_chatbot/langchain_poc.py`: reusable LangChain Runnable and LCEL POC helpers.
- `src/sst_chatbot/rag_poc.py`: RAG and retriever POC helpers.
- `src/sst_chatbot/ards_generator.py`: generated ARDS/SDD bundle and user workspace POC helpers.
- `labs/notebooks/langchain_lcel_poc.ipynb`: manual POC notebook with mock and OpenAI modes.
- `labs/experiments/`: scratch experiments that are not production contracts.
- `tests/`: pytest suite using mocks/fakes for external provider behavior.
- `.env` and `jupyter_settings.py`: local-only configuration. Do not commit secrets.
- `.env.example`: committed placeholder environment file.
- `docs/architecture/agent-runtime-product-intent.md`: business and product direction for the governed agent runtime.

## Build, Test, And Development Commands
Use the project virtual environment instead of the system Python.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe init.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts\ards_check.py
.\.venv\Scripts\python.exe scripts\check.py
```

Notes:
- `init.py` requires provider environment variables.
- Unit tests must not require real OpenAI, LangSmith, Anthropic, Deepseek, or other external service calls.
- The notebook defaults to mock mode so it can run without paid API quota.
- `scripts/check.py` is the repo-level validation entrypoint.

## Coding Style
- Follow standard Python conventions: 4-space indentation, explicit imports, `snake_case` for functions and variables, `PascalCase` for classes.
- Keep scripts thin; move reusable behavior into `src/sst_chatbot/`.
- Put new maintainable agent code under `src/app/` unless a task explicitly targets the older `src/sst_chatbot/` modules.
- Keep provider SDK usage behind replaceable helpers or adapters.
- Keep provider/model/memory choices parameterized through `Settings` and `src/app/providers/`.
- Keep SST core prompts in the private prompt engine; do not store prompt bodies in LangSmith.
- Prefer small functions with clear side effects around API calls, environment loading, and provider selection.
- Keep internal ARDS/SDD knowledge separate from generated user ARDS/SDD workspaces.
- Do not let agent output become files directly; use structured intent plus deterministic backend validation.

## POC Rules
- Put notebooks under `labs/notebooks/`.
- Put non-notebook experiments under `labs/experiments/`.
- Add a spec under `specs/pocs/` for durable POCs.
- Keep mock or fake execution paths for local development.
- Promote code into `src/` only after it has tests and documented provider assumptions.
- If a POC is discarded, update its spec with the reason before removing related files.

## Testing Guidelines
- Use `pytest`.
- Mock external providers in unit tests.
- Cover provider abstraction, configuration loading, structured output, and failure paths.
- Manual provider checks belong in notebooks or explicit integration scripts, not unit tests.

## Security And Configuration
- Never commit live API keys or secrets.
- Keep `.env` local and rotate exposed credentials immediately.
- Document required variables with placeholder values only.
- Treat debug logs, caches, notebook checkpoints, and virtual environments as generated state.

## Agent Operating Policies

Before planning or executing a task, agents must review and apply the adopted ARDS/SDD operating policies for this repo.

Registry principal:

- `specs/integration/policies.yaml`

Human-readable policy entrypoint:

- `docs/policies/README.md`

Inherited policies:

- `agent-model-selection-policy`
- `agent-resource-degradation-policy`
- `agent-task-atomization-policy`
- `agent-delegation-policy`
- `agent-context-management-policy`
- `agent-architecture-boundary-policy`
- `visual-documentation-as-code-policy`
- `human-doc-language`
- `owner-documentation-authority-policy`
- `control-plane-link-policy`
- `http-qa-harness-policy` (`exception-open`/`not-applicable` hasta que exista una superficie HTTP propia)

These policies are inherited from `4uentes-ards-core` and adopted locally through scoped manifests. They complement local specs, docs, capabilities, handoffs, and working agreements. They do not replace functional contracts, ownership, or product architecture.

