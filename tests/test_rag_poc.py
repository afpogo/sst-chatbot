from langchain_core.documents import Document

from sst_chatbot.rag_poc import (
    RetrieverConfig,
    SourceDocument,
    build_rag_chain_with_retriever,
    build_mock_rag_chat_model,
    build_rag_chain,
    build_sample_rag_index,
    build_sst_retriever,
    format_context,
    load_source_documents,
    retrieve_relevant_documents,
    split_documents,
)


def test_load_source_documents_preserves_metadata() -> None:
    documents = load_source_documents(
        [
            SourceDocument(
                source_id="doc-1",
                title="Document 1",
                content="Contenido sobre ARDS y SST.",
                workspace_id="workspace-a",
            )
        ]
    )

    assert len(documents) == 1
    assert documents[0].metadata["source_id"] == "doc-1"
    assert documents[0].metadata["workspace_id"] == "workspace-a"


def test_split_documents_creates_safe_chunks() -> None:
    document = Document(
        page_content=" ".join(["ARDS"] * 120),
        metadata={"source_id": "doc-1"},
    )

    chunks = split_documents([document], chunk_size=80, chunk_overlap=10)

    assert len(chunks) > 1
    assert chunks[0].metadata["chunk_index"] == 0
    assert all(len(chunk.page_content) <= 80 for chunk in chunks)


def test_retrieve_relevant_documents_filters_by_workspace() -> None:
    documents = load_source_documents(
        [
            SourceDocument(
                source_id="doc-a",
                title="ARDS A",
                content="ARDS para workspace A",
                workspace_id="a",
            ),
            SourceDocument(
                source_id="doc-b",
                title="RAG B",
                content="RAG para workspace B",
                workspace_id="b",
            ),
        ]
    )

    results = retrieve_relevant_documents("RAG", documents, workspace_id="b")

    assert len(results) == 1
    assert results[0].document.metadata["source_id"] == "doc-b"


def test_format_context_includes_source_metadata() -> None:
    index = build_sample_rag_index()
    retrieved = retrieve_relevant_documents("Que template ARDS basico puedo usar?", index)

    context = format_context(retrieved)

    assert "source=template-ards-basic" in context
    assert "Template ARDS/SDD basico" in context


def test_retrieve_relevant_documents_supports_threshold() -> None:
    index = build_sample_rag_index()

    retrieved = retrieve_relevant_documents(
        "template ARDS descargable",
        index,
        search_type="similarity_score_threshold",
        score_threshold=2,
    )

    assert retrieved
    assert all(item.score >= 2 for item in retrieved)


def test_sst_retriever_invokes_with_mmr_strategy() -> None:
    index = build_sample_rag_index()
    retriever = build_sst_retriever(
        index,
        RetrieverConfig(search_type="mmr", top_k=2, fetch_k=3),
    )

    documents = retriever.invoke("template ARDS agentes")

    assert len(documents) <= 2
    assert any(document.metadata["source_id"] == "template-ards-basic" for document in documents)


def test_rag_chain_answers_with_mock_model() -> None:
    chain = build_rag_chain(
        build_mock_rag_chat_model(),
        build_sample_rag_index(),
    )

    result = chain.invoke({"question": "Que template ARDS/SDD puede descargar el usuario?"})

    assert "estructura ARDS/SDD" in result
    assert "Fuentes:" in result


def test_rag_chain_can_use_retriever_contract() -> None:
    index = build_sample_rag_index()
    retriever = build_sst_retriever(
        index,
        RetrieverConfig(search_type="similarity", top_k=2),
    )
    chain = build_rag_chain_with_retriever(build_mock_rag_chat_model(), retriever)

    result = chain.invoke({"question": "Como generar un ZIP ARDS/SDD seguro?"})

    assert "backend genere el ZIP" in result
