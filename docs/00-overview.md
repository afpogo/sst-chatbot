# SST Chatbot Agent Repository Overview

## Purpose
This repository is the experimentation and integration base for AI agents that can feed SST and future applications.

The repo must remain provider-agnostic. OpenAI, Anthropic, Deepseek, local models, or any future provider should be replaceable behind stable internal contracts.

## Current State
- Primary future application package under `src/app/`.
- Existing reusable SST POC modules under `src/sst_chatbot/`.
- Laboratory notebooks under `labs/notebooks/`.
- Unit tests under `tests/`.
- Environment loading through `.env` with committed placeholders in `.env.example`.
- OpenAI is currently the first real provider experiment.
- ARDS/SDD documentation under `docs/` and structured contracts under `specs/`.
- A governed, read-only user-memory RAG kernel under `src/app/governed_rag/`, validated with deterministic fakes and not yet connected to the chat runtime.
- Plaud transcript derivations are documented as an asynchronous cross-repo handoff through `4uentes-orchestor`, with production Plaud ingestion staying in `sst-bend`.
- Repository synchronization is now documented as a tri-repo contract: `sst-chatbot` adopts policy from `4uentes-ards-core` and hands structured execution intents to `4uentes-orchestor`.
- Model and subagent selection policy lives in `docs/playbooks/model-selection-policy.md`.

## Product Intent
This repository is intended to become the governed agent runtime core for SST, not only a chatbot or LangChain experimentation area.

The product direction is documented in `docs/architecture/agent-runtime-product-intent.md` and `specs/architecture/agent-runtime-product-intent.yaml`.

The core business workflow is:

```text
operational context
  -> governed memory
  -> private versioned prompts
  -> provider-agnostic model execution
  -> structured validated intent
  -> ARDS/SDD memory, workspace proposal, or orchestrator handoff
```

## ARDS/SDD Structure
- `AGENTS.md`: operational guide for humans and AI agents working in this repo.
- `docs/`: human-readable context, architecture notes, ADRs, playbooks, POC policies, and task logs.
- `specs/`: machine-readable or semi-structured source of truth for capabilities, integrations, POCs, architecture, and future states.
- `src/app/`: maintainable base for future agents, graphs, tools, prompts, schemas, memory, and LLM client boundaries.
- `src/sst_chatbot/`: existing reusable modules promoted from earlier POCs.
- `labs/`: exploratory notebooks and experiments that are not production contracts.
- `tests/`: automated validation, with external providers mocked by default.

## LangChain, LangGraph, LangSmith, And OpenAI
- LangChain is the future composition layer for model calls and chains.
- LangGraph is reserved for future graph-based agent workflows.
- LangSmith is enabled through environment configuration for manual tracing.
- OpenAI initialization is isolated behind `src/app/llm/openai_client.py`.
- Provider/model/memory swapping is parameterized through `src/app/providers/` and `.env`.
- Core prompts are managed by a private repo-owned engine under `src/app/prompts/`.
- Prompt lifecycle guidance for agents and humans lives in `docs/playbooks/05-author-and-validate-prompts.md`.

## Cross-Repo Plaud Derivations
- Architecture: `docs/architecture/plaud-sst-orchestrator-agent-derivations.md`
- Integration contract: `specs/integrations/plaud-sst-orchestrator-derivations.yaml`
- Agent capability: `specs/capabilities/plaud-transcript-derivations.yaml`
- Operational note: `docs/tasks/2026-05-24-plaud-sst-orchestrator-handoff.md`
- Model selection annex: `docs/playbooks/model-selection-policy.md`

## Cross-Repo Core And Orchestrator Sync
- Sync contract: `specs/integrations/sst-chatbot-core-orchestrator-sync.yaml`
- Local binding: `specs/ards/contract-binding.yaml`
- Core policy adoption: `specs/integration/policies.yaml`
- Orchestrator boundary: `specs/capabilities/agent-lifecycle-and-orchestrator-boundary.yaml`

## RAG gobernado de memoria de usuario

- Arquitectura owner: `docs/architecture/governed-user-memory-rag.md`.
- Capability: `specs/capabilities/retrieval-augmented-generation.yaml`.
- Estado local: `specs/states/sst-user-governed-rag-v1.yaml`.
- El núcleo actual usa fakes y no conecta persistencia, vector store, chat realtime ni un proveedor real.

## Out Of Scope
- Business logic.
- Functional production agents.
- Complex LangGraph workflows.
- External API calls in unit tests.
- Provider-specific coupling outside adapter boundaries.
- Undeclared provider SDKs for Anthropic, GitHub Copilot, Deepseek, or local runtimes.
- LangSmith-owned prompt storage for SST core prompts.

## Validation
Use the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts\ards_check.py
.\.venv\Scripts\python.exe scripts\check.py
```

`scripts/check.py` is the repo-level validation entrypoint. Unit tests should not call real external providers.
