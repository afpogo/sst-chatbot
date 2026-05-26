# RAG POC Implementation

## What This POC Demonstrates
This POC replicates the course concept of RAG using the repository's current constraints:
- no paid provider calls in tests;
- no vector database yet;
- LangChain-compatible `Document` objects;
- LCEL chain composition;
- SST-oriented metadata and source handling.

The implemented flow is:

```text
SourceDocument
  -> load_source_documents
  -> split_documents
  -> SSTRetriever / retrieve_relevant_documents
  -> format_context
  -> ChatPromptTemplate | chat_model | StrOutputParser
```

## Files
- `src/sst_chatbot/rag_poc.py`: implementation.
- `tests/test_rag_poc.py`: unit tests.
- `labs/notebooks/langchain_rag_poc.ipynb`: manual demonstration.
- `specs/capabilities/retrieval-augmented-generation.yaml`: capability spec.
- `specs/pocs/langchain-rag-poc.yaml`: POC registry entry.

## Design Notes
The loader and splitter are local functions for now because the environment does not include `langchain_community` or `langchain_text_splitters`. The POC still uses LangChain's `Document`, `ChatPromptTemplate`, `RunnableLambda`, and LCEL composition.

The retriever is intentionally simple and lexical. It supports `similarity`, `similarity_score_threshold`, and a local MMR-style strategy. That is enough to prove the architecture and tests. A later version can replace the retrieval implementation with embeddings and a vector store without changing the SST-facing contract.

## Why The Backend Owns Retrieval
The LLM should not decide which private documents it can access. The backend must filter by workspace, account, permissions, and document metadata before context reaches the model.

This is the same principle used for ARDS/SDD file generation: the model proposes or answers, while deterministic backend code validates and executes sensitive operations.

## Internal Vs Generated ARDS/SDD
The POC now treats retrieved documents as internal generation knowledge: template catalog, safe generation rules, and maturity rules. That context helps the agent decide what structure to generate for the user.

The generated ARDS/SDD package is a separate output. It should be created by `ards_generator.py` and delivered as a ZIP after backend validation.
