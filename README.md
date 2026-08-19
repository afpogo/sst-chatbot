# SST Chatbot Agent Lab

Python repository for AI-driven development around LangChain, LangGraph, LangSmith, OpenAI, and future provider-agnostic agents.

## Structure
- `src/app/`: primary maintainable application package for future agents.
- `src/app/audience_access/`: governed SST user/stakeholder access and grounded metric explanation contracts.
- `src/app/governed_rag/`: governed, provider-agnostic user-memory retrieval kernel with deterministic fakes.
- `src/sst_chatbot/`: existing reusable POC-promoted SST modules kept for compatibility.
- `labs/`: notebooks and exploratory experiments.
- `docs/`: human-readable ARDS/SDD documentation, ADRs, and playbooks.
- `specs/`: structured ARDS/SDD contracts and indexes.
- `tests/`: automated validation with mocked external providers.

## Setup
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill `.env` locally. Do not commit secrets.

## Validation
```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts\ards_check.py
.\.venv\Scripts\python.exe scripts\smoke_governed_rag.py
.\.venv\Scripts\python.exe scripts\smoke_stakeholder_rag.py
.\.venv\Scripts\python.exe scripts\check.py
```

Unit tests must not call OpenAI, LangSmith, or any other external provider.

## Runtime HTTP de desarrollo

El runtime interno se empaqueta como contenedor no privilegiado:

```powershell
docker build -t sst-chatbot:local .
docker run --rm -p 8091:8091 sst-chatbot:local
```

`GET /healthz` es la única ruta no autenticada. Los turnos entran por
`POST /internal/v1/chat/turns` con el JWT M2M definido en
`specs/integrations/sst-realtime-chat-runtime.yaml`.

GitHub Actions runs the same repository gate on `main`, `develop`, `agent/**`
and pull requests. It also enforces at least 90% line coverage for
`src/app/governed_rag`.
Stakeholder/audience-access changes also enforce at least 90% line coverage for
`src/app/audience_access`.
