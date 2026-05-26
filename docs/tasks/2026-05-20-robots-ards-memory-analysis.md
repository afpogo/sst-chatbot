# Robots ARDS Memory Analysis

## Context
`CR-SST-0006` reported that Robots exists as a documented SST domain with partial backend persistence in `sst-bend`, but it is not a complete runtime feature across SST.

This note preserves the current interpretation for `sst_chatbot`.

## Classification
Robots should be treated as ARDS memory and planning evidence, not as an executable runtime feature.

Recommended status:
- `sst-bend`: `runtime-partial`
- cross-repo runtime: `not-implemented`
- memory status: `candidate`
- safe chatbot intents: `user_history.propose_update`, `workspace.generate_bundle`
- blocked intents: `workspace.apply_patch`, `server.restart_service`, `server.refresh_cache`

## Memory Mapping
Robots discovery should create candidate memory records with:
- domain: `robots`
- kind: `evidence`, `gap`, `task`
- scope: `cross_repo`
- source: `repo_discovery`
- visibility: `internal`
- indexable: true
- downloadable: false

## Implementation Implication
The agent core can reason about Robots and produce ARDS/SDD plans. It must not assume Robots endpoints, UI, extension support, or infrastructure manifests exist until those gaps are closed in the relevant repos.

The application connector model should allow Robots to know the SST application context where they reside. Until runtime connectors exist, a file connector descriptor can carry the domain and scope contract.
