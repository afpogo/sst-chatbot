# Tasks And Operational States

This directory records durable task context, state scenarios, and follow-up work that should survive across AI sessions.

Use it for:
- implementation notes that affect future work;
- state-machine style gaps;
- cross-repo coordination notes;
- decisions that are too small for an ADR but too important to leave in chat.

Do not use it for transient logs, raw debug output, or secrets.

## Current Task Backlog
- Define the first SST API boundary for user workspace provisioning.
- Define the first SST event boundary for agent lifecycle creation and orchestrator handoff.
- Decide the initial allowlist of operation intent types for user history, UI customization, and future `4uentes-orchestor` handoff.
- Add machine-readable state scenarios for agent lifecycle before integrating with `4uentes-orchestor`.
- Define the first normalized activity event schema for chat messages, Articles, Dictionary, Bitacoras, and Robots discovery.
- Add validation for internal ARDS memory tags, provenance, visibility, and lifecycle status.
- Build a file-based application connector descriptor before requiring runtime event delivery.
- Use `CR-SST-0006` Robots context as discovery evidence, not runtime authorization.
- Add a generated workspace manifest model and tests.
- Decide whether `runtime_validation_playground.ipynb` should be archived or removed.
- Keep lifecycle and orchestrator-boundary POCs isolated under `pocs/` until tests and handoff boundaries are stable.
- Keep Plaud transcript derivations asynchronous through `4uentes-orchestor`; do not make Plaud sync depend on chatbot completion.

## Latest Summary
- `docs/tasks/2026-08-13-governed-user-memory-rag.md`
- `docs/tasks/2026-08-10-llm-provider-smoke.md`
- `docs/tasks/2026-05-24-plaud-sst-orchestrator-handoff.md`
- `docs/tasks/2026-04-27-session-summary.md`
