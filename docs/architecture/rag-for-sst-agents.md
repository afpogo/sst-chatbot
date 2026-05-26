# RAG For SST Agents

## Goal
RAG should be a context capability for SST agents. It should not become the whole agent architecture or couple SST to LangChain, OpenAI, embeddings, or a specific vector database.

The application-facing contract should stay stable:

```text
SST
  -> agent contract
  -> optional retrieval
  -> provider adapter
  -> normalized answer with sources
```

## Why It Matters
LLMs do not know private, recent, or workspace-specific SST data. RAG adds that context at request time by loading documents, splitting them into chunks, retrieving relevant chunks, and injecting those chunks into the prompt.

Useful SST sources include:
- internal ARDS/SDD docs, specs, templates, and generation rules;
- meeting notes and project decisions;
- internal functional documentation;
- articles, dictionaries, tickets, and troubleshooting notes;
- generated artifacts that were previously approved.

For the ARDS/SDD generation agent, the first retrieval source should be internal ARDS/SDD knowledge. The generated ARDS/SDD bundle is a user artifact and should remain separate unless the user later chooses to index it as project context.

## Initial POC Architecture
The first POC intentionally avoids a real vector database. It proves the contract with local documents and deterministic retrieval.

Layers:
- Ingestion: convert repo-owned source records into LangChain `Document` objects.
- Indexing: split documents into chunks with metadata.
- Retrieval: select relevant chunks through a retriever contract.
- Answer chain: use LCEL to compose retrieval context, prompt, model, and parser.

## Safety And Multi-Tenant Rules
- Every indexed document needs metadata such as `workspace_id`, `source_id`, `document_type`, and `title`.
- Retrieval must filter by workspace or account before ranking.
- Answers should include sources when based on private context.
- Unit tests must not require provider calls or paid quota.
- Future vector stores must preserve the same metadata filtering behavior.
- Internal ARDS/SDD and generated ARDS/SDD must not be mixed in the same corpus without explicit ownership metadata.

## Evolution Path
After the local POC, the next implementation steps are:
- replace lexical retrieval with embeddings;
- add a vector store behind a repository-owned interface;
- add reranking or hybrid search if needed;
- add evaluation questions to measure retrieval quality;
- expose retrieval as an optional capability in the SST agent contract.
