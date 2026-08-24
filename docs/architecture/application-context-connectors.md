# Application Context Connectors

## Goal
Define an application-agnostic connector model so SST robots and agents can understand the application where they reside.

The connector should describe application domains, event types, capabilities, permissions, and context sources without coupling the agent core to one SST module.

## Why This Exists
SST currently has or will have domains such as:
- Articles;
- Dictionary;
- Bitacoras;
- Robots.

Robots need scope. A robot assigned to an account or application should know which domains exist, which events matter, which actions are allowed, and which memory records it may read or produce.

## Design Direction
Use a small repo-owned connector contract that can be implemented in two ways:
- runtime connector: an application emits normalized events and exposes context through an API or message channel;
- file connector: a project includes a checked-in descriptor that documents domains, events, permissions, and ARDS mapping.

The file connector is the fallback path when a project cannot expose runtime events yet.

## Event Envelope
The normalized event should follow the CloudEvents shape where practical:
- `id`
- `source`
- `type`
- `subject`
- `time`
- `datacontenttype`
- `dataschema`
- `data`

The `data` payload remains application-specific. The envelope stays stable.

## Connector Metadata
Each connector should declare:
- application id;
- application name;
- domains;
- event types;
- entity types;
- capability scopes;
- permission hints;
- memory tag mapping;
- retrieval scope rules;
- supported intents;
- blocked intents.

## Robots Scope Rules
A robot should receive context only for:
- its account or tenant;
- the application where it resides;
- the domains assigned to it;
- the intents allowed by its role and lifecycle status;
- memory records marked as visible and indexable for that robot scope.

For Robots in SST, the current discovery state is `runtime-partial`; this means robots can be represented in memory and planning, but should not be treated as a complete runtime feature yet.

## First Connector Candidates
- `sst.articles`: article lifecycle and editorial decisions.
- `sst.dictionary`: terms, domain language, definitions, and semantic changes.
- `sst.bitacoras`: operational notes, state changes, and audit-like user records.
- `sst.robots`: robot lifecycle evidence, gaps, permissions, and runtime-readiness state.

## Implementation Phases
1. Define `application_context_connector` as a YAML template.
2. Build a mock connector in this repository for Articles, Dictionary, Bitacoras, and Robots.
3. Convert connector events into `user_activity_ards_memory` records.
4. Add retrieval filters by application id, account id, domain, and robot role.
5. Document an AsyncAPI boundary for runtime event delivery.
6. Let consuming apps adopt either runtime events or the file connector.

## Non-Goals
- This repository should not own production event brokers.
- This repository should not mutate application databases.
- This repository should not grant robot permissions by itself.
- This repository should not depend on one application domain to understand all others.

## Principal verificado y data products seguros

Todo connector que alimente una experiencia de audiencia debe propagar un
`PrincipalContext` afirmado por `sst_backend`. El descriptor declara además el
mapeo de clasificación, los data products seguros y la metadata de divulgación.
El connector no autentica, no infiere entitlements y no transforma texto del
prompt en permisos.

Para `sst_user`, cada envelope coincide exactamente en tenant, usuario y
aplicación. Para `sst_stakeholder`, el único data product inicial es un snapshot
global de `approved_analytics`, con definición, período, cohorte, supresión y
provenance. `restricted` y `secret` nunca son elegibles para retrieval, provider,
trace ni audit.
