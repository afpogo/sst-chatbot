# Agent Core And Orchestrator Boundary

## Goal
Prepare this repository to become the core for creating SST agents and managing their local proposal lifecycle.

Server orchestration is a separate responsibility owned by the `4uentes-orchestor` repository. This repository defines the agent-side contracts and local proposal behavior that can request orchestrator review through structured, validated intents.

## Baseline From Idea Intake
The April 10 idea note introduces three durable directions:
- user context and activity history should be editable through agent-guided workflows;
- agent work should be regulated by a state machine that reacts to events;
- UI or workspace customization should be queued and processed asynchronously, preferably during low-traffic windows.

These ideas fit the existing repository rule: agents propose structured intent, while deterministic backend services validate and execute. In the server case, execution belongs to `4uentes-orchestor`, not to this repository.

## Repository Role
This repository should own:
- agent creation contracts;
- local agent lifecycle state models for proposal preparation;
- provider-agnostic agent contracts;
- agent-side state machines for planning, validation handoff, and local lifecycle tracking;
- POCs that prove agent behavior with mocks before integration with `4uentes-orchestor`;
- reusable Python modules promoted from POCs after tests and documented assumptions;
- validation rules for generated files, workspace mutations, and operation intent requests.

It should not directly own:
- production infrastructure credentials;
- uncontrolled filesystem writes on SST servers;
- server orchestration workers;
- production queues for server-side work;
- provider-specific behavior in SST-facing contracts;
- irreversible server operations without deterministic validation, audit, and permission checks.

## `4uentes-orchestor` Role
The `4uentes-orchestor` repository should own:
- server-side orchestration;
- production worker execution;
- durable queues and scheduling policies for server operations;
- infrastructure adapters;
- permission checks tied to deployment/runtime concerns;
- execution audit records for server mutations.

This repository can define the payload shape that an agent emits, but `4uentes-orchestor` owns whether, when, and how that payload is accepted, queued, scheduled, or executed.

## Target Flow
```text
SST application event
  -> local agent proposal contract in this repository
  -> local agent proposal state machine
  -> optional provider call
  -> structured operation intent
  -> orchestrator integration boundary
  -> 4uentes-orchestor validation, queue, schedule, or rejection
  -> auditable result
```

The same boundary should cover generated ARDS/SDD workspaces, user history update proposals, UI customization requests, and future server maintenance actions.

## Local Agent State Responsibilities
The local agent state model should make proposed agent work explicit and inspectable before any handoff to `4uentes-orchestor`. These states are not `4uentes-orchestor` request lifecycle states.

Initial candidate states:
- `requested`: SST or a user requested agent work.
- `classified`: the request was mapped to a known capability.
- `planned`: the agent returned structured proposal data or a backend planner produced a deterministic local plan.
- `validated_for_handoff`: local checks accepted the intent shape for an orchestrator handoff.
- `handoff_requested`: an orchestrator request was emitted.
- `handoff_accepted`: `4uentes-orchestor` accepted ownership of execution.
- `completed`: the agent lifecycle completed after receiving an accepted result.
- `failed`: execution failed with a normalized reason.
- `rejected`: validation or policy blocked the request.

State transitions should be event-driven and should record actor, timestamp, input reference, output reference, and external orchestrator correlation id when applicable.

## Orchestrator Handoff Boundary
Server manipulation must be expressed as operation intents, not free-form commands. This repository can create and test proposal payloads; `4uentes-orchestor` accepts, schedules, executes, or rejects them.

Initial operation intent types:
- `workspace.generate_bundle`
- `workspace.apply_patch`
- `user_history.propose_update`
- `ui_customization.enqueue_change`

Future blocked operation types:
- `server.restart_service`
- `server.refresh_cache`

Server operations stay blocked until RBAC, audit, rollback, scheduling policy, and approval gates exist.

The first promoted implementation should avoid real production server actions. POCs in this repository should use a fake orchestrator client that records requested operations and validates lifecycle transitions.

## Local Fake Adapter

The CR-SST-0022 adapter is local test infrastructure. It validates handoff payloads, records in-memory receipts, and returns local statuses such as `accepted_for_review`, `rejected_by_policy`, `duplicate`, and `conflict`.

`accepted_for_review` does not mean `queued`, `running`, or approved for execution. It only means the local fake boundary accepted the proposal shape for review.

## Handoff Payload
The handoff payload should include:
- operation intent id;
- tenant or account scope;
- user scope when applicable;
- capability id;
- validated intent payload;
- priority;
- preferred execution window;
- requested retry policy;
- idempotency key;
- audit metadata.

Offline execution windows are scheduling policy hints. `4uentes-orchestor` decides when work is allowed to run.

## POC Boundary
POCs for this direction belong under `pocs/` and `specs/pocs/`.

The first POC should prove:
- a mock SST event can enter an agent lifecycle state model;
- a mock agent or deterministic planner can return structured operation intent;
- local validation can accept or reject that intent shape for handoff;
- human-reviewed proposal work can be recorded by a fake orchestrator client;
- a fake orchestrator response can complete the agent lifecycle without touching a real server.
- duplicate and conflicting idempotency keys are handled deterministically.

Promotion into `src/` requires tests, a spec, and clear evidence that provider calls and orchestrator integration remain replaceable.

## Open Decisions
- Which SST events should start an agent lifecycle first?
- Which operation intents should be handed to `4uentes-orchestor` first?
- Which parts of state are owned here versus persisted by `4uentes-orchestor`?
- What permission model gates user history edits and UI customization?
- Which low-traffic scheduling hints should this repo emit, and which policies should remain fully inside `4uentes-orchestor`?
