# Playbook 03: LangSmith Tracing

## Objective
Enable LangSmith tracing for future manual runs while keeping unit tests provider-free.

## Preconditions
- A LangSmith API key is available for manual runs.
- `.env` exists locally and is not committed.
- The code path being traced is a manual script, notebook, or future integration check.

## Commands
```powershell
notepad .env
```

Set:

```env
LANGCHAIN_API_KEY=your-local-key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=agentic-python-lab
```

Then run the manual script or notebook that uses LangChain.

## Expected Result
LangChain traces appear in the configured LangSmith project for manual runs.

## Common Problems
- `LANGCHAIN_TRACING_V2=true` without `LANGCHAIN_API_KEY` will not produce traces.
- Unit tests should not assert against LangSmith remote state.
- Project names should be explicit so traces are not mixed across experiments.

## Success Validation
Confirm the manual run appears under `LANGCHAIN_PROJECT` in LangSmith.
