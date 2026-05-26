# Session Summary 2026-04-27

## Purpose
This note preserves the current state of the repository and the product decisions made so future sessions do not depend on chat history.

## What Was Built
- ARDS/SDD repository base with `docs/`, `specs/`, `pocs/`, `scripts/`, and `AGENTS.md`.
- Repo-level validation through `scripts/ards_check.py` and `scripts/check.py`.
- LangChain LCEL POC with `invoke`, `batch`, `stream`, mock mode, and OpenAI mode.
- LangChain chat roles POC for `system`, `user`, and `assistant` messages.
- RAG POC with ingestion, chunking, retrieval, prompt augmentation, and mock generation.
- Retriever strategy POC with `similarity`, `similarity_score_threshold`, and local MMR-style retrieval.
- ARDS/SDD bundle generator POC with ZIP export.
- User workspace provisioning POC with `logical`, `physical`, and `hybrid` storage modes.

## Core Product Decisions
- SST should remain provider-agnostic. OpenAI is an experiment, not the architecture.
- LangChain can be used for orchestration, but SST-facing contracts should not expose LangChain types.
- RAG is an optional context capability for agents, not the whole agent architecture.
- Retrievers are the right abstraction for SST. Vector stores are one possible backend.
- Internal ARDS/SDD and generated ARDS/SDD are separate concepts.
- Internal ARDS/SDD feeds retrievers, planners, validators, and governance.
- Generated ARDS/SDD belongs to the user/account/project and can be downloaded or evolved.
- Agents should produce structured intent or plans; deterministic backend code should create files, directories, ZIPs, and persistent records.

## Current Architecture Direction
The intended user flow is:

```text
user created or user request
  -> user workspace provisioning
  -> optional retriever over internal ARDS/SDD knowledge
  -> agent planner
  -> structured generation intent
  -> backend validator
  -> deterministic generator
  -> logical workspace and/or downloadable ZIP
```

## Current Validation State
The latest full repository check passed with:

```powershell
.\.venv\Scripts\python.exe scripts\check.py
```

Expected result at the time of this note:
- `ARDS/SDD check passed`
- `23 passed`
- `Repository check passed`

## Next Candidate Work
- Add a generated workspace manifest model to prevent uncontrolled growth.
- Define file lifecycle states: `draft`, `active`, `archived`, `discarded`.
- Define flags for `downloadable`, `indexable`, and `user_visible`.
- Add a POC for patching an existing generated workspace instead of duplicating whole structures.
- Define the first API boundary SST would call for workspace provisioning.
