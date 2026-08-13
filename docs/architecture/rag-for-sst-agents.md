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

## Vector Retrieval Lifecycle

The embeddings course material should be adopted as an architecture pattern for future vector database work, not only as an implementation detail. The pattern turns documents into auditable, searchable context for the chatbot core.

Recommended lifecycle:

```text
source document
  -> normalize text and required metadata
  -> build canonical text representation
  -> validate token budget
  -> split into chunks with overlap
  -> generate one embedding per chunk
  -> persist vector + chunk text + metadata
  -> query embedding
  -> vector similarity search
  -> metadata filtering
  -> optional deduplication or reranking
  -> final context for the answer chain
```

This lifecycle gives SST a stable retrieval pattern independent of the first vector store. The same contract can be backed by an in-memory test store, FAISS, pgvector, Milvus, or another dedicated vector database.

The key architectural rule is that a vector record is not just a vector. It must preserve enough metadata to enforce governance and traceability:

- `chunk_id` and `source_id`;
- `workspace_id` and account or tenant scope;
- `source_tier` and `origin`;
- `embedding_model`, `embedding_dimension`, and `pipeline_version`;
- eligibility flags such as `indexable`, `visible_to_user`, and lifecycle status.

If the embedding model, chunking logic, or metadata contract changes, the index should be treated as versioned state and rebuilt or migrated deliberately.

## Safety And Multi-Tenant Rules
- Authorization by tenant, user, application, entitlements, classification and source must finish before ranking, not only before prompt assembly.
- Every indexed document needs metadata such as `workspace_id`, `source_id`, `document_type`, and `title`.
- Retrieval must filter by workspace or account before ranking.
- Answers should include sources when based on private context.
- Unit tests must not require provider calls or paid quota.
- Future vector stores must preserve the same metadata filtering behavior.
- Internal ARDS/SDD and generated ARDS/SDD must not be mixed in the same corpus without explicit ownership metadata.
- Vector indexes must preserve embedding model and pipeline version metadata so retrieval results remain auditable.
- Restricted, secret, credential-like, inactive and non-indexable records must never reach a retriever or provider adapter.
- Provider output must use structured claims whose citations are validated against the retrieved chunk set.

## Implementación gobernada local

CR-SST-0155 promueve estas reglas a `src/app/governed_rag/` con ports y fakes
deterministas. La explicación completa vive en
`docs/architecture/governed-user-memory-rag.md`. Este corte no está conectado
al runtime HTTP del chat y no adopta todavía base vectorial ni proveedor real.

## Evolution Path
After the local POC, the next implementation steps are:
- replace lexical retrieval with embeddings;
- add a vector store behind a repository-owned interface;
- add reranking or hybrid search if needed;
- add evaluation questions to measure retrieval quality;
- expose retrieval as an optional capability in the SST agent contract.
