# Proofs Of Concept

This directory contains POC policy and legacy context. Active laboratory notebooks and scratch experiments live under `labs/`.

POCs are not production contracts. Durable behavior should move into `src/`, be covered by tests, and be documented under `specs/`.

## Layout
- `../labs/notebooks/`: exploratory notebooks.
- `../labs/experiments/`: scratch experiments.
- `../specs/pocs/`: durable POC contracts.

## Current Entries
- `../labs/notebooks/langchain_lcel_poc.ipynb`: LangChain Runnable and LCEL experiment with mock and OpenAI modes.
- `../labs/notebooks/langchain_chat_roles_poc.ipynb`: chat roles experiment using `system`, `user`, and `assistant` messages through LCEL.
- `../labs/notebooks/langchain_rag_poc.ipynb`: RAG experiment with SST documents, chunking, retrieval, context injection, and sources.
- `../labs/notebooks/runtime_validation_playground.ipynb`: earlier configuration/import validation notebook kept for review.
- `src/sst_chatbot/ards_generator.py`: deterministic backend generator used by the ARDS/SDD generation agent POC.
