# Generated Workspace Governance

## Goal
Generated ARDS/SDD workspaces must not become uncontrolled dumps of chat history, duplicate files, or irrelevant agent output.

The user should be able to interact freely with the agent, but only curated, validated artifacts should enter the generated workspace.

## Three Storage Categories
SST should separate:
- conversation history: temporal, auditable, not directly downloadable as ARDS/SDD;
- workspace files: curated generated artifacts that belong to the user workspace;
- retrieval index: filtered content that can be used as context later.

Not every conversation becomes a file. Not every file becomes retrieval context. Not every retrieval document becomes downloadable.

## Manifest Requirement
Every generated workspace should have a manifest, eventually stored as `.sst/manifest.yaml` or an equivalent logical record.

The manifest should track:
- path;
- kind;
- status;
- source;
- related feature or decision;
- version;
- user visibility;
- download eligibility;
- retrieval eligibility.

Example:

```yaml
version: 1
kind: generated_workspace_manifest
files:
  - path: specs/features/user-onboarding.yaml
    kind: feature_spec
    status: active
    source: agent_generated
    downloadable: true
    indexable: true
    user_visible: true
  - path: docs/archive/old-draft.md
    kind: archive
    status: archived
    source: agent_generated
    downloadable: false
    indexable: false
    user_visible: false
```

## Lifecycle States
- `draft`: generated but not accepted as stable workspace content.
- `active`: accepted and part of the current generated workspace.
- `archived`: retained for traceability but excluded from normal downloads and retrieval.
- `discarded`: rejected or superseded; should not be used as context.

## Anti-Redundancy Rules
- The agent should propose a patch when a related file exists.
- The backend should reject duplicate paths unless the operation is an explicit update.
- Generated files should have a kind and a status before entering the workspace.
- RAG should exclude archived, discarded, and temporary content by default.
- Downloads should include only files marked as downloadable.
- Retrieval should include only files marked as indexable and allowed for the current user/account.

## Backend Responsibility
The backend owns workspace governance. The LLM can propose structure, edits, or summaries, but deterministic code should decide what enters the manifest, what is downloadable, and what can be indexed.
