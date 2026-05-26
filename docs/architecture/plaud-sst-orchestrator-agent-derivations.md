# Plaud, SST, Orchestrator, And Agent Derivations

## Goal
Document the cross-repo architecture for Plaud transcript ingestion, agent-generated document derivations, and orchestrator handoff.

This repository owns the agent-side analysis, contracts, prompt/provider boundaries, and structured outputs. It does not own Plaud production sync, SST article persistence, or production job orchestration.

## Repositories
- `sst-bend`: owns Plaud webhook/sync, transcript persistence, `article_payloads`, `article_documents`, and SST HTTP contracts.
- `sst_chatbot`: owns provider-agnostic agents, prompts, structured derivation outputs, ARDS memory classification, and mock/POC validation.
- `4uentes-orchestor`: owns cross-repo execution, queues, retries, scheduling, permission checks, and durable orchestration audit.
- `node-auth` / BFF: exposes consumer-facing pass-through or facade surfaces when needed.
- frontend/extension consumers: read final SST documents and user-visible states through BFF/SST contracts.

## Recommended Flow
```text
Plaud webhook or sync
  -> sst-bend persists transcript as article payload
  -> sst-bend registers requested article document derivations
  -> sst-bend emits a derivation request to 4uentes-orchestor
  -> 4uentes-orchestor schedules and calls sst_chatbot
  -> sst_chatbot generates structured translation, summary, or memory candidates
  -> 4uentes-orchestor returns accepted result or failure to sst-bend
  -> sst-bend persists article_documents and exposes status/content
```

The Plaud sync path must not synchronously depend on `sst_chatbot`. A failed or delayed agent derivation must not break Plaud ingestion.

## Ownership Rules
- Plaud credentials and webhook secrets stay outside this repository.
- `sst-bend` remains the source of truth for article and document state.
- `sst_chatbot` never mutates SST databases directly.
- Agent output is structured intent/result data, not direct filesystem or database writes.
- `4uentes-orchestor` owns execution timing, retries, idempotency, and cross-repo audit.
- The same transcript can produce user-visible documents and internal ARDS memory, but these outputs must be tracked separately.

## Derivation Types
Initial agent derivations:
- `translation`: translate transcript or article context into a target language.
- `summary`: generate a normalized summary document.
- `memory_candidates`: classify transcript evidence into governed ARDS memory candidates.

Out of scope for the first handoff:
- live Plaud MCP production sync;
- direct audio processing;
- direct writes from this repository into `sst-bend`;
- frontend-specific rendering decisions;
- server restarts or infrastructure mutations.

## Runtime Boundary
The durable runtime boundary should be event/job based:

```text
document_derivation.requested
document_derivation.accepted
document_derivation.completed
document_derivation.failed
```

The orchestrator may implement this as HTTP, queue, or internal worker handoff, but this repository should keep the agent contract transport-agnostic.

## Failure Model
- If Plaud sync succeeds and derivation fails, the transcript remains available in SST.
- If `sst_chatbot` is unavailable, `4uentes-orchestor` retries or marks the derivation failed according to policy.
- If an agent result fails validation, the orchestrator rejects it before returning it to SST.
- If SST cannot persist a completed result, SST owns the retry/idempotency outcome for document state.

## ARDS Memory Rule
Plaud transcripts can become internal ARDS memory only through governed classification:

```text
raw transcript
  -> normalized transcript evidence
  -> memory candidates
  -> approval or lifecycle transition
  -> indexable memory
```

Raw transcripts must not automatically become generated user ARDS/SDD files.

## Implementation Notes
The first implementation should use mocks/fakes in this repository:
- fake SST derivation request;
- fake orchestrator client;
- deterministic validation for structured agent outputs;
- mocked provider response.

Only after the POC is stable should `4uentes-orchestor` call a real `sst_chatbot` runtime.
