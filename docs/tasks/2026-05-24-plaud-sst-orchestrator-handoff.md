# Plaud SST Orchestrator Handoff

## Context
Plaud MCP is available for exploration, but the product path should keep Plaud production ingestion in `sst-bend` and route cross-repo agent work through `4uentes-orchestor`.

The goal is to let Plaud transcripts produce translations, summaries, and governed ARDS memory without coupling `sst-bend` directly to chatbot internals or provider SDKs.

## Decision
Use an asynchronous cross-repo handoff:

```text
sst-bend -> 4uentes-orchestor -> sst_chatbot -> 4uentes-orchestor -> sst-bend
```

`sst-bend` persists the transcript first. The orchestrator owns execution, retries, idempotency, and audit. `sst_chatbot` owns agent contracts and structured outputs.

## Artifacts Added
- `docs/architecture/plaud-sst-orchestrator-agent-derivations.md`
- `specs/integrations/plaud-sst-orchestrator-derivations.yaml`
- `specs/capabilities/plaud-transcript-derivations.yaml`

## Open Work
- Define the exact orchestrator transport: HTTP, queue, or worker handoff.
- Define the first fake orchestrator client POC in this repo.
- Add structured schemas for derivation request and response.
- Add tests for translation, summary, memory candidates, and rejection paths.
- Publish matching outbound capability in `sst-bend` if the SST runtime contract changes.
- Create or update orchestrator-side inbound/adoption docs when `4uentes-orchestor` is ready.

## Non-Goals
- Do not move Plaud credentials into this repository.
- Do not make Plaud sync wait for agent completion.
- Do not let agent output write directly to SST databases.
- Do not use Plaud MCP as the first production sync mechanism.
