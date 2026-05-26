# User Workspace ARDS/SDD

## Goal
When a user is created in SST, the platform should provision a user-scoped ARDS/SDD workspace. That workspace is the user's generated structure, not the internal ARDS/SDD used to build this product.

## Internal Vs Generated
Internal ARDS/SDD:
- belongs to the SST product and engineering process;
- stores architecture, specs, templates, policies, and approved examples;
- feeds retrievers and validators;
- is not downloaded directly by users.

Generated ARDS/SDD:
- belongs to a specific user, account, or project;
- is created from validated templates and generation rules;
- can exist as logical records, physical directories, or both;
- can be exported as a downloadable ZIP.

## Provisioning Trigger
The first trigger is user signup or account onboarding.

```text
user created
  -> workspace provisioning request
  -> generated ARDS/SDD layout
  -> logical and/or physical storage
  -> downloadable artifact when requested
```

## Storage Modes
- `logical`: store file records, metadata, and content in a database or object model.
- `physical`: create directories and files in controlled storage.
- `hybrid`: persist metadata logically and materialize files for export or processing.

The POC starts with logical layout generation. Physical writes should be added only behind backend validation and controlled storage roots.

## Minimum Generated Workspace
Each user workspace should start with:
- `AGENTS.md`;
- `docs/00-overview.md`;
- `docs/adr/0001-adopt-ards-sdd.md`;
- `specs/00-index.yaml`;
- `specs/templates/feature.template.yaml`;
- `specs/templates/state-scenario.template.yaml`;
- `scripts/check.py`;
- `.sst/workspace.yaml`.

## Backend Responsibilities
- Generate stable workspace IDs.
- Validate storage mode.
- Reject unsafe paths.
- Keep internal templates separate from generated user content.
- Export ZIPs without exposing internal product docs.
- Add tenant/account metadata for future retrieval filters.
- Maintain a manifest so the workspace does not accumulate redundant, irrelevant, or unsafe generated files.

## Governance Requirement
A generated workspace should not store everything the user says to the agent. It should store curated files with lifecycle metadata.

The workspace should separate:
- conversation history;
- generated workspace files;
- retrieval index content.

See `docs/architecture/generated-workspace-governance.md` for the candidate governance model.
