# User Activity ARDS Memory

## Goal
Capture relevant SST user activity as governed internal ARDS memory, then use that memory to generate curated ARDS/SDD artifacts when appropriate.

This is a separate concern from server orchestration. The chatbot and agent core should understand, classify, tag, and propose artifacts. Runtime execution remains behind explicit backend or orchestrator boundaries.

## Problem
SST already has application domains such as Articles, Dictionary, and soon Bitacoras. Robots will add operational actors that need to understand the application where they reside.

The system needs a way to record what users decide, comment, ask, and discover while interacting with the chatbot without turning raw chat into uncontrolled files.

## Three-Layer Model
```text
application activity and chatbot conversation
  -> normalized activity events
  -> tagged internal ARDS memory
  -> curated ARDS/SDD workspace artifacts
```

The first layer is evidence. The second layer is governed memory. The third layer is user-facing or project-facing documentation.

## Internal Memory Rules
- Raw conversation history must not automatically become ARDS/SDD files.
- Every memory record needs tags, provenance, visibility, and lifecycle status.
- Memory can be indexable for RAG without being downloadable.
- Memory can be user-visible without being promoted into workspace files.
- Corrections and invalidations should be new records or state transitions, not silent edits.
- Generated ARDS/SDD artifacts should cite or reference the memory records they derived from.

## Candidate Event Classes
- `sst.chat.message.captured`
- `sst.user_comment.captured`
- `sst.user_decision.recorded`
- `sst.article.created`
- `sst.article.updated`
- `sst.dictionary.term.created`
- `sst.dictionary.term.updated`
- `sst.bitacora.entry.created`
- `sst.robot.discovery.recorded`
- `ards.memory.promoted`
- `ards.entity.status_changed`

## Governance Tags
Initial tag groups:
- `domain`: `articles`, `dictionary`, `bitacoras`, `robots`, `accounts`, `auth`, `ards`
- `kind`: `comment`, `decision`, `evidence`, `gap`, `risk`, `task`, `requirement`, `state_change`
- `scope`: `user`, `account`, `workspace`, `feature`, `repo`, `cross_repo`
- `visibility`: `internal`, `user_visible`, `downloadable`, `indexable`
- `status`: `draft`, `candidate`, `active`, `archived`, `discarded`
- `source`: `chatbot`, `application_event`, `repo_discovery`, `orchestrator_handoff`, `manual_import`

Tags must be stored as structured attributes, not inferred only from text.

## Provenance Model
Use a lightweight mapping inspired by W3C PROV:
- `Agent`: SST user, robot, chatbot agent, backend service, orchestrator job.
- `Activity`: capture comment, classify memory, propose artifact, approve decision, invalidate memory.
- `Entity`: comment, decision, evidence record, gap, generated spec, ADR, ARDS bundle.

Important relations:
- `was_derived_from`: generated artifact or decision derived from a conversation, discovery, or event.
- `was_attributed_to`: user, robot, or agent responsible for the record.
- `was_revision_of`: revised memory or artifact.
- `was_invalidated_by`: correction, deletion, or superseding event.

## Robots Context From CR-SST-0006
The Robots discovery handoff should enter memory as evidence, not as runtime authorization.

Recommended classification:
- domain: `robots`
- kind: `evidence`, `gap`, `task`
- scope: `cross_repo`
- status: `candidate`
- source: `repo_discovery`

Safe intents:
- `user_history.propose_update`
- `workspace.generate_bundle`

Blocked until a later authorization path:
- `workspace.apply_patch`
- `server.restart_service`
- `server.refresh_cache`

## Implementation Phases
1. Define the memory record schema and tag taxonomy.
2. Add a deterministic classifier that maps normalized activity events to memory candidates.
3. Add governance validation for tags, visibility, lifecycle status, and provenance.
4. Add a mock event source for Articles, Dictionary, Bitacoras, chat messages, and Robots discovery.
5. Add a generator path that can produce ARDS/SDD bundles from approved memory records.
6. Add retrieval filters so robots can see only memory in their account, application, and capability scope.
7. Integrate with the real SST event boundary after the POC proves the contract.

## External References
- CloudEvents: https://github.com/cloudevents/spec
- AsyncAPI: https://www.asyncapi.com/docs/reference/specification/v3.0.0
- W3C PROV: https://www.w3.org/ns/prov
- OpenTelemetry Logs Data Model: https://opentelemetry.io/docs/specs/otel/logs/data-model/
- Event Sourcing: https://www.martinfowler.com/eaaDev/EventSourcing.html
