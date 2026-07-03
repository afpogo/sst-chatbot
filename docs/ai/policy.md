# AI Policy

## Purpose

This document is the agent-facing policy entrypoint for `sst-chatbot`.
It summarizes the local ARDS/SDD operating boundary and points agents to the
canonical policy registry before planning or executing work.

## Required Sources

Before planning or changing this repo, agents must review:

- `AGENTS.md`
- `specs/integration/policies.yaml`
- `docs/policies/README.md`
- `specs/integrations/sst-chatbot-core-orchestrator-sync.yaml`

The canonical ARDS/SDD policy source is `4uentes-ards-core`. This repo adopts
scoped local policy artifacts and does not redefine the shared canon.

## Runtime Boundary

`sst-chatbot` prepares provider-agnostic agent outputs, validates structured
operation intents, and may exercise local fake orchestrator handoff tests.

It must not:

- execute SST server work directly;
- mutate SST services, user workspaces, or infrastructure directly;
- own production scheduling, retries, queues, or audit;
- treat prompt or provider output as accepted business state.

`4uentes-orchestor` owns acceptance, queueing, retry policy, scheduling, audit,
and cross-repo reconciliation after a handoff is accepted.

## Handoff Transport

The local fake orchestrator adapter is test infrastructure only. The real
transport remains undecided and must stay open until an approved request selects
HTTP, queue, worker, or another explicit mechanism.

## Agent Work Rules

- Use structured intents and deterministic validation before handoff.
- Keep provider, model, retriever, and memory choices configurable.
- Keep private prompts internal and metadata-only in traces.
- Record missing information as `TODO` instead of inventing state.
- Preserve `orchestrator_link` metadata for cross-repo reconciliation.
- Keep local ARDS/SDD artifacts aligned with the control-plane lifecycle.

## Validation

Run the local checks with:

```powershell
.\.venv\Scripts\python.exe scripts\ards_check.py
.\.venv\Scripts\python.exe scripts\check.py
```

