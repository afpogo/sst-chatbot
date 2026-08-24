# Retrievers For SST Agents

## Why Retrievers Matter
A retriever is the contract that receives a natural language query and returns relevant documents. It is more general than a vector store.

A vector store stores embeddings and can retrieve similar documents. A retriever only promises retrieval. It may use a vector store, lexical search, hybrid search, metadata filters, MMR, reranking, or a combination of strategies.

For SST, the application should depend on the retriever contract, not on a specific vector database.

## Why This Is Better Than Thinking Only In Vectors
Vectors are an implementation detail for semantic similarity. They are useful, but they do not solve the whole retrieval problem.

SST needs retrieval that also understands:
- workspace and account filtering;
- template categories;
- document types;
- maturity levels;
- diversity of context;
- source traceability;
- security constraints.

The retriever layer combines relevance strategies without exposing the storage engine to the rest of the app. Authorization remains a separate earlier boundary: the retriever receives only an already-authorized projection and cannot grant access.

## Límite promovido por CR-SST-0155

El contrato mantenible vive en `src/app/governed_rag/ports.py`. Su
`RetrieverPort` recibe exclusivamente `AuthorizedChunk`; tenant, usuario,
aplicación, entitlements, clasificación, fuente, estado, indexabilidad y
contenido sensible ya fueron evaluados por el policy gate. Los filtros físicos
de un futuro vector store son defensa en profundidad y no reemplazan esa
decisión determinística.

## Search Strategies
- `similarity`: good default for finding the closest matching chunks.
- `similarity_score_threshold`: useful when the agent should say it lacks context instead of using weak matches.
- `mmr`: useful when repeated chunks are likely; it balances relevance and diversity.
- `hybrid`: future option combining lexical search, vector search, metadata filters, and reranking.

## Retriever configuration contract (RAF/POC)

The POC in `src/sst_chatbot/rag_poc.py` uses a small immutable configuration object for retrieval behavior:

```python
@dataclass(frozen=True)
class RetrieverConfig:
    search_type: str = "similarity"
    top_k: int = 3
    fetch_k: int = 8
    score_threshold: float = 0.0
    lambda_mult: float = 0.5
    workspace_id: str | None = None
    strategy: str = "lexical"
    embedding_query_fn: Callable[[str], list[float]] | None = None
    embedding_document_vectors: list[list[float]] | None = None
```

What this means in architecture terms:

- `RetrieverConfig(...)` is object construction for the config value object, not a direct runtime provider call.
- `@dataclass` generates constructor and utility methods automatically (`__init__`, `__repr__`, `__eq__`), avoiding manual boilerplate.
- With `frozen=True`, the config is immutable after creation, which keeps retrieval decisions auditable and avoids accidental mutation between requests.
- Attributes are plain object fields (no implicit C#-style getters/setters); consumers read/write through the object attributes.
- `workspace_id` becomes a first-class input to enforce tenant-scoped filtering inside the retrieval contract.

Field intent:

- `search_type`: algorithm choice at runtime (`similarity`, `similarity_score_threshold`, `mmr`).
- `top_k`: number of chunks finally returned to the answer chain.
- `fetch_k`: pre-retrieval candidate pool size before final selection/reranking.
- `score_threshold`: minimum relevance score when using score-gated strategies.
- `lambda_mult`: MMR diversity control (higher => less redundancy).
- `workspace_id`: mandatory tenant/context guardrail for correctness and isolation.
- `strategy`: backend strategy signal (`lexical`, `embeddings`) used to keep current POC deterministic while allowing later migration.
- `embedding_query_fn` / `embedding_document_vectors`: optional fields for embedding-aware retrieval; they can remain unused in lexical mode and become active in embedding strategy.

Implementation note:

- `score_threshold` is numeric relevance score dependent, so it should be treated as `float`.
- Validation belongs to config construction (`__post_init__` when needed) rather than retrieval call sites, to keep policy boundaries clean and deterministic.

This keeps the architecture goal aligned: the retriever contract controls policy and behavior, while the provider-specific retrieval backend remains replaceable.

## Chatbot Retrieval Topology (Current POC)

The chatbot in SST should retrieve context from two retriever layers:

1. Internal governance corpus
2. User workspace corpus (`generated ARDS/SDD`)

For the current POC, only internal governance corpus is guaranteed available at runtime.
The user corpus exists as a logical ARDS/SDD workspace that starts generic and can later be specialized.

```text
user question
  -> intent classification
  -> retriever policy selection
    -> internal corpus (guidance, platform semantics, generation rules)
    -> user workspace corpus (if synced and explicitly indexed)
  -> answer chain
  -> response with source traceability
```

The important boundary remains:

- Internal corpus documents are for product governance and should never be overwritten by user interactions.
- User corpus documents are generated/updated by backend flows (`sync -> validate -> index`), not by raw LLM output.
- Mixed retrieval is allowed only through explicit metadata policies (`source_tier`, `workspace_id`, `origin`, `kind`).

## Recommended SST Use
For the ARDS/SDD generation agent, retrievers should search internal generation knowledge:
- template catalog;
- safe generation rules;
- maturity model;
- approved examples;
- output file policies.

The retriever should not search the user's generated ZIP as if it were product governance. Generated ARDS/SDD may later be indexed as user-owned project context, but it remains separate from the internal knowledge base.

## Candidate Implementation Path
Start with a local retriever contract in the POC. Then replace the internal scoring with:
- embeddings and vector store for semantic search;
- metadata filters for workspace and template type;
- MMR for diverse context;
- reranking when the corpus grows.

The public agent flow should not change when the retrieval engine changes.
