# Agent Runtime Product Intent

## Purpose
This repository is not intended to become only a LangChain playground or a generic chatbot. Its product direction is to become the governed agent runtime core for SST and future applications.

The business goal is to convert operational context into structured, auditable, and safe agent work:

```text
events, conversations, transcripts, comments, and user requests
  -> governed context and memory
  -> versioned private prompts
  -> provider-agnostic model execution
  -> structured validated intent
  -> ARDS/SDD memory, workspace proposal, or orchestrator handoff
```

## Business Thesis
SST needs robots and agents that understand application context, preserve useful operational knowledge, and propose safe actions without bypassing governance.

The repository should optimize for:
- capturing business and operational knowledge that would otherwise be lost;
- converting that knowledge into structured ARDS/SDD memory;
- creating agents on demand from governed capabilities;
- producing auditable operation intents instead of free-form actions;
- handing execution to the external ARDS/SDD and server orchestrator boundary when execution is required.

## Product Boundaries
This repository owns the agent-side reasoning core:
- application context normalization;
- governed memory contracts;
- private prompt management;
- provider/model/memory configuration;
- agent lifecycle state;
- structured intent generation;
- local deterministic validation before handoff.

It does not own:
- production server execution;
- direct filesystem or infrastructure mutation from model output;
- unrestricted autonomous agents;
- LangSmith-owned prompt storage;
- raw chat history as durable memory;
- provider-specific behavior leaking into SST-facing contracts.

## Priority Use Cases
1. Plaud and transcript derivations: convert transcripts into decisions, tasks, gaps, specs, and memory candidates.
2. Agent creation on demand: classify a user request and produce a governed agent creation intent.
3. ARDS/SDD memory: convert useful events and conversations into scoped, tagged, provenance-aware memory.
4. Operation intents: emit validated work requests such as workspace generation, user history proposals, or orchestrator handoff.
5. Cross-repo orchestration: hand execution to `4uentes-orchestor` or a future ARDS/SDD orchestrator through explicit contracts.

## Strategic Architecture
The system should evolve through layered contracts:

```text
Application Context
  -> Memory Layer
  -> Prompt Layer
  -> Provider Layer
  -> Agent Lifecycle
  -> Intent Layer
  -> Orchestrator Boundary
```

Each layer must remain independently testable and replaceable. Prompts must not own memory retrieval. Providers must not own business decisions. Agents must not execute operations directly.

## Next Product Milestone
The next implementation milestone should be a minimal Agent Runtime Core centered on `agent_creation_intent`.

Candidate input:
- `tenant_id`
- `user_id`
- `application_id`
- `user_request`
- `available_capabilities`
- optional governed context

Candidate output:
- `agent_intent_id`
- `capability_id`
- `prompt_id`
- `prompt_version`
- `provider`
- `model`
- `required_memory`
- `required_tools`
- `allowed_intents`
- `blocked_intents`
- `validation_status`
- `audit_metadata`

This milestone turns the current infrastructure into a business workflow: request in, governed agent intent out.

## Success Metrics
The product should be evaluated by:
- time from request to validated intent;
- classification accuracy for known capabilities;
- percentage of unsafe intents rejected by policy;
- amount of useful ARDS/SDD memory generated from events and transcripts;
- reduction of manual work to produce summaries, specs, gaps, and tasks;
- traceability of each output to prompt id, prompt version, model, memory sources, and capability;
- zero intentional leakage of private prompts or sensitive context into external observability.

## Brainstorming Rules
Future brainstorming should be evaluated against the product thesis:
- Does it improve governed knowledge capture?
- Does it improve safe agent creation or lifecycle control?
- Does it improve structured intent quality?
- Does it reduce operational risk?
- Does it preserve ARDS/SDD traceability?

Ideas that only add model features, provider variety, or prompt complexity without improving these outcomes should remain secondary.
