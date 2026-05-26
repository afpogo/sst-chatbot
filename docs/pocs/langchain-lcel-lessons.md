# LangChain Runnable And LCEL Lessons For This Repository

## Relevant Lessons
Runnable and LCEL are useful for this repository because they separate AI workflows into composable units:
- `invoke` fits one-off user requests from SST or a web UI.
- `batch` fits repeated generation or validation tasks over multiple specs, files, or prompts.
- `stream` fits interactive UX where the user sees progress while an agent reasons or drafts output.
- `PromptTemplate | model | parser` gives a readable path from request to structured output.
- Structured output is the important bridge between an LLM response and backend actions.
- Chat roles are part of the agent contract: `system` defines behavior, `user` carries the request, and `assistant` can provide examples or previous context.

## Repository Implications
For SST agent work, the LLM should not be treated as the system of record. It should produce structured decisions, manifests, plans, or drafts. Deterministic backend code should validate and execute those results.

This matters most for file generation. A future web user may ask for an internal ARDS/SDD package. The agent can infer the desired structure, but the backend should materialize the files from a validated manifest or template.

## Pattern To Keep
Use LCEL for orchestration:

```text
user request
  -> role-aware prompt template
  -> provider model
  -> structured output parser
  -> backend validator
  -> deterministic generator
  -> downloadable bundle
```

The first three steps are AI-assisted. The last three steps are deterministic and testable.

## Why This Supports Provider Agnosticism
If the repo owns the structured output schema and the generator, providers can change without changing the SST-facing behavior. OpenAI, Anthropic, Deepseek, or local models only need to satisfy the same schema.
