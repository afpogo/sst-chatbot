# ADR 0001: Python Agentic Project Structure

## Status
Accepted.

## Context
The repository already had reusable SST POC modules under `src/sst_chatbot/`, notebooks under `pocs/notebooks/`, ARDS/SDD documentation, specs, and pytest coverage. The next phase needs a professional base for future LangChain, LangGraph, LangSmith, and OpenAI work without mixing production-oriented code with exploratory notebooks.

## Decision
Use `src/app` as the primary maintainable application package for new agentic code.

Use `labs/notebooks` and `labs/experiments` for exploratory work. Existing notebooks were moved from `pocs/notebooks` to `labs/notebooks` because notebooks are laboratory assets, while durable POC contracts remain under `specs/pocs`.

Keep `src/sst_chatbot` in place for existing reusable modules and tests. Future promotion or consolidation should be handled by a separate migration ADR.

## Consequences
- New source code has a stable home in `src/app`.
- Notebooks are clearly separated from maintainable application code.
- ARDS/SDD specs continue to index durable decisions and POCs.
- No business logic, functional agents, or complex LangGraph workflows are introduced by this base structure.

## Validation
Run:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts\ards_check.py
.\.venv\Scripts\python.exe scripts\check.py
```
