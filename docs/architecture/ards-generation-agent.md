# ARDS/SDD Generation Agent

## Goal
Allow a user to request an ARDS/SDD structure from a web experience and download the generated package when ready.

The agent should help decide what structure and content are needed, but it should not write arbitrary files directly. The backend should validate the request and generate a controlled bundle.

## Recommended Web Flow

```text
Frontend
  -> user request
  -> backend API
  -> LangChain LCEL chain
  -> structured generation request
  -> backend ARDS generator
  -> in-memory bundle
  -> downloadable zip
```

## Responsibilities
- Frontend: collect the user's goal, display progress, and expose a download button.
- Agent chain: interpret the request and return a structured ARDS generation intent.
- Backend validator: reject unsafe paths, oversized content, unsupported templates, and malformed output.
- Generator: create the predefined ARDS/SDD structure from templates.
- Download service: return a ZIP or persist a temporary artifact under controlled storage.

## File And Directory Creation
Yes, this type of agent can create files and directories for a user, but the safe design is indirect:
- The LLM proposes a manifest or fills predefined template fields.
- The backend validates every path and every allowed file type.
- Deterministic code creates the final files or ZIP.
- The frontend offers the generated package for download.

This avoids letting the model perform arbitrary filesystem writes. It also makes the feature testable without API quota.

## Initial POC Shape
The first POC should generate an ARDS/SDD bundle in memory:
- `AGENTS.md`
- `docs/00-overview.md`
- `docs/adr/0001-adopt-ards-sdd.md`
- `specs/00-index.yaml`
- `specs/templates/feature.template.yaml`
- `specs/templates/state-scenario.template.yaml`
- `scripts/check.py`

The generated bundle can be exported as ZIP bytes for a future web download endpoint.

## User Workspace Provisioning
The same generation primitive can be used during user onboarding. Instead of only producing a ZIP on demand, the backend can create a generated ARDS/SDD workspace scoped to the user or account.

The workspace can be:
- logical, stored as metadata and file records;
- physical, materialized as directories and files;
- hybrid, with metadata persisted and files materialized for export.

The agent should not own this provisioning step directly. It can suggest structure and content, but backend code must create the workspace through validated templates.
