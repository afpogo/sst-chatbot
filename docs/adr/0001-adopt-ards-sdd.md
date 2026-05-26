# ADR 0001: Adopt ARDS/SDD For This Repository

## Status
Accepted

## Context
This repository is intended to evolve from isolated AI experiments into a reusable agent integration base for SST and future systems.

Without a repo-local documentation and specification structure, provider experiments can become hard to trace, hard to test, and too coupled to the first provider used.

## Decision
Adopt ARDS/SDD as the repository operating model:
- `docs/` for human-readable context, architecture, decisions, POCs, and tasks;
- `specs/` for structured source of truth;
- `AGENTS.md` as the operational guide;
- `pocs/` for experiments before promotion to reusable code;
- `tests/` as the validation path.

## Consequences
- New durable behavior should be backed by a spec or ADR.
- POCs should not silently become application code.
- Provider-specific logic must be isolated behind replaceable adapters or capability contracts.
- Unit tests must use mocks or fakes for external providers by default.
