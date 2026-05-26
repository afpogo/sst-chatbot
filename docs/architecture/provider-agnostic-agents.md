# Provider-Agnostic Agent Architecture

## Goal
The repository should produce reusable AI agent capabilities for SST without binding SST to a specific AI provider.

Provider-specific SDKs are implementation details. The repo-owned contracts should describe what an agent can do: chat, stream, batch, return structured output, retrieve private context, and eventually call tools.

## Architecture Direction
The target flow is:

```text
SST or future app
  -> agent capability contract
  -> optional retrieval capability
  -> provider adapter
  -> external provider or local model
```

The application should not know whether a response came from OpenAI, Anthropic, Deepseek, or a local model. It should receive normalized outputs and normalized failures.

For file generation use cases, the application should receive validated manifests or generated bundles. Provider output must not directly become filesystem writes.

## Provider Adapter Responsibilities
- Load provider configuration without exposing secrets.
- Convert internal message inputs into the provider format.
- Normalize text responses, streamed chunks, structured outputs, and errors.
- Expose a stable interface for tests and POCs.
- Support a no-cost mock implementation for local development.
- Return structured file-generation intent when an agent is asked to create ARDS/SDD structures.
- Accept retrieved context without knowing which vector store or retrieval strategy produced it.

## POC Promotion Rule
A POC can move into `src/` only when it has:
- a documented spec under `specs/pocs/`;
- a clear capability it proves;
- mocked unit tests;
- documented provider assumptions;
- a path to replace or add providers without changing SST-facing behavior.

## Initial Provider Status
OpenAI through LangChain is the first real provider experiment. It is not the architectural default. The repo default for repeatable tests remains mock/local behavior.
