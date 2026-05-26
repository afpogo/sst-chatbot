# POC Policy

POCs are allowed and expected in this repo, but they must remain separated from reusable implementation.

## Location
- Put notebooks in `labs/notebooks/`.
- Put scratch experiments in `labs/experiments/`.
- Put short POC specs in `specs/pocs/`.
- Promote reusable code into `src/sst_chatbot/` only after the POC has tests.

## Required POC Metadata
Each durable POC should define:
- goal;
- provider or framework used;
- required environment variables;
- whether it has a mock mode;
- what capability it proves;
- criteria to promote, keep, or discard.

## Current POCs
- LangChain LCEL POC: `labs/notebooks/langchain_lcel_poc.ipynb`.
- LangChain chat roles POC: `labs/notebooks/langchain_chat_roles_poc.ipynb`.
- LangChain RAG POC: `labs/notebooks/langchain_rag_poc.ipynb`.
- Runtime validation playground: `labs/notebooks/runtime_validation_playground.ipynb`.
- ARDS/SDD generation agent POC: `src/sst_chatbot/ards_generator.py`.
