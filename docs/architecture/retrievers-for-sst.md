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

The retriever layer gives us a place to combine those rules without exposing the storage engine to the rest of the app.

## Search Strategies
- `similarity`: good default for finding the closest matching chunks.
- `similarity_score_threshold`: useful when the agent should say it lacks context instead of using weak matches.
- `mmr`: useful when repeated chunks are likely; it balances relevance and diversity.
- `hybrid`: future option combining lexical search, vector search, metadata filters, and reranking.

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
