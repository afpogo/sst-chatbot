from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable

from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnableLambda


@dataclass(frozen=True)
class SourceDocument:
    source_id: str
    title: str
    content: str
    document_type: str = "note"
    workspace_id: str = "default"


@dataclass(frozen=True)
class RetrievedDocument:
    document: Document
    score: int


@dataclass(frozen=True)
class RetrieverConfig:
    search_type: str = "similarity"
    top_k: int = 3
    fetch_k: int = 8
    score_threshold: int = 1
    lambda_mult: float = 0.5
    workspace_id: str | None = None


def load_source_documents(sources: Iterable[SourceDocument]) -> list[Document]:
    documents: list[Document] = []
    for source in sources:
        documents.append(
            Document(
                page_content=source.content,
                metadata={
                    "source_id": source.source_id,
                    "title": source.title,
                    "document_type": source.document_type,
                    "workspace_id": source.workspace_id,
                },
            )
        )
    return documents


def split_documents(
    documents: Iterable[Document],
    chunk_size: int = 450,
    chunk_overlap: int = 80,
) -> list[Document]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be zero or lower than chunk_size")

    chunks: list[Document] = []
    for document in documents:
        text = " ".join(document.page_content.split())
        start = 0
        chunk_index = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end].strip()
            if chunk_text:
                metadata = dict(document.metadata)
                metadata["chunk_index"] = chunk_index
                chunks.append(Document(page_content=chunk_text, metadata=metadata))
                chunk_index += 1

            if end == len(text):
                break
            start = end - chunk_overlap

    return chunks


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2
    }


def _document_tokens(document: Document) -> set[str]:
    tokens = tokenize(document.page_content)
    tokens.update(tokenize(str(document.metadata.get("title", ""))))
    tokens.update(tokenize(str(document.metadata.get("document_type", ""))))
    return tokens


def _token_overlap_score(query_tokens: set[str], document: Document) -> int:
    return len(query_tokens.intersection(_document_tokens(document)))


def _document_diversity_penalty(document: Document, selected: list[Document]) -> float:
    if not selected:
        return 0.0

    document_tokens = _document_tokens(document)
    if not document_tokens:
        return 0.0

    max_similarity = 0.0
    for selected_document in selected:
        selected_tokens = _document_tokens(selected_document)
        union = document_tokens.union(selected_tokens)
        if not union:
            continue
        similarity = len(document_tokens.intersection(selected_tokens)) / len(union)
        max_similarity = max(max_similarity, similarity)
    return max_similarity


def retrieve_relevant_documents(
    query: str,
    documents: Iterable[Document],
    top_k: int = 3,
    workspace_id: str | None = None,
    search_type: str = "similarity",
    score_threshold: int = 1,
    fetch_k: int = 8,
    lambda_mult: float = 0.5,
) -> list[RetrievedDocument]:
    if search_type not in {"similarity", "similarity_score_threshold", "mmr"}:
        raise ValueError(f"Unsupported search_type: {search_type}")

    query_tokens = tokenize(query)
    scored: list[RetrievedDocument] = []

    for document in documents:
        if workspace_id and document.metadata.get("workspace_id") != workspace_id:
            continue

        score = _token_overlap_score(query_tokens, document)
        if score > 0:
            scored.append(RetrievedDocument(document=document, score=score))

    scored.sort(
        key=lambda item: (
            item.score,
            str(item.document.metadata.get("source_id", "")),
            -int(item.document.metadata.get("chunk_index", 0)),
        ),
        reverse=True,
    )

    if search_type == "similarity_score_threshold":
        scored = [item for item in scored if item.score >= score_threshold]

    if search_type == "mmr":
        selected: list[RetrievedDocument] = []
        candidates = scored[:fetch_k]

        while candidates and len(selected) < top_k:
            selected_documents = [item.document for item in selected]
            best_item = max(
                candidates,
                key=lambda item: (
                    lambda_mult * item.score
                    - (1 - lambda_mult)
                    * _document_diversity_penalty(item.document, selected_documents)
                ),
            )
            selected.append(best_item)
            candidates.remove(best_item)

        return selected

    return scored[:top_k]


class SSTRetriever(BaseRetriever):
    documents: list[Document]
    config: RetrieverConfig = RetrieverConfig()

    def _get_relevant_documents(self, query: str, *, run_manager: Any) -> list[Document]:
        retrieved = retrieve_relevant_documents(
            query,
            self.documents,
            top_k=self.config.top_k,
            workspace_id=self.config.workspace_id,
            search_type=self.config.search_type,
            score_threshold=self.config.score_threshold,
            fetch_k=self.config.fetch_k,
            lambda_mult=self.config.lambda_mult,
        )
        return [item.document for item in retrieved]


def build_sst_retriever(
    indexed_documents: list[Document],
    config: RetrieverConfig | None = None,
) -> SSTRetriever:
    return SSTRetriever(documents=indexed_documents, config=config or RetrieverConfig())


def format_context(retrieved_documents: Iterable[RetrievedDocument]) -> str:
    blocks: list[str] = []
    for item in retrieved_documents:
        metadata = item.document.metadata
        title = metadata.get("title", "Untitled")
        source_id = metadata.get("source_id", "unknown")
        chunk_index = metadata.get("chunk_index", 0)
        blocks.append(
            f"[source={source_id} chunk={chunk_index} score={item.score}] "
            f"{title}: {item.document.page_content}"
        )
    return "\n\n".join(blocks) if blocks else "No se recupero contexto relevante."


def build_rag_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "Sos un asistente RAG para SST. Responde solo con el contexto "
                    "recuperado. Si el contexto no alcanza, decilo explicitamente. "
                    "Inclui una seccion breve de fuentes."
                ),
            ),
            (
                "human",
                "Pregunta:\n{question}\n\nContexto recuperado:\n{context}",
            ),
        ]
    )


def build_rag_chain(
    chat_model: Runnable[Any, Any],
    indexed_documents: list[Document],
    top_k: int = 3,
) -> Runnable[dict[str, Any], str]:
    def prepare(input_value: dict[str, Any]) -> dict[str, str]:
        question = str(input_value["question"])
        workspace_id = input_value.get("workspace_id")
        retrieved = retrieve_relevant_documents(
            question,
            indexed_documents,
            top_k=top_k,
            workspace_id=str(workspace_id) if workspace_id else None,
        )
        return {
            "question": question,
            "context": format_context(retrieved),
        }

    return RunnableLambda(prepare) | build_rag_prompt() | chat_model | StrOutputParser()


def build_rag_chain_with_retriever(
    chat_model: Runnable[Any, Any],
    retriever: BaseRetriever,
) -> Runnable[dict[str, Any], str]:
    def prepare(input_value: dict[str, Any]) -> dict[str, str]:
        question = str(input_value["question"])
        documents = retriever.invoke(question)
        retrieved = [
            RetrievedDocument(document=document, score=0)
            for document in documents
        ]
        return {
            "question": question,
            "context": format_context(retrieved),
        }

    return RunnableLambda(prepare) | build_rag_prompt() | chat_model | StrOutputParser()


def build_mock_rag_chat_model() -> Runnable[Any, AIMessage]:
    def respond(input_value: Any) -> AIMessage:
        messages = input_value.to_messages() if hasattr(input_value, "to_messages") else input_value
        text = "\n".join(getattr(message, "content", "") for message in messages)

        if "No se recupero contexto relevante" in text:
            return AIMessage(
                content=(
                    "No tengo contexto suficiente para responder con precision.\n\n"
                    "Fuentes: sin fuentes recuperadas."
                )
            )

        if "template" in text.lower() or "ARDS" in text or "SDD" in text:
            return AIMessage(
                content=(
                    "Para generar una estructura ARDS/SDD, el agente debe recuperar "
                    "templates internos, reglas de paths permitidos y criterios de "
                    "madurez; luego debe devolver un plan estructurado para que el "
                    "backend genere el ZIP.\n\n"
                    "Fuentes: catalogo interno de generacion ARDS/SDD."
                )
            )

        if "retriever" in text.lower() or "recuper" in text.lower():
            return AIMessage(
                content=(
                    "El retriever debe actuar como contrato de recuperacion: puede "
                    "usar similitud, umbral o MMR sin exponer el motor interno a SST.\n\n"
                    "Fuentes: catalogo interno de generacion ARDS/SDD."
                )
            )

        return AIMessage(
            content=(
                "La respuesta debe generarse a partir del contexto recuperado.\n\n"
                "Fuentes: contexto recuperado de documentos SST."
            )
        )

    return RunnableLambda(respond)


def build_sample_sst_documents() -> list[SourceDocument]:
    return [
        SourceDocument(
            source_id="template-ards-basic",
            title="Template ARDS/SDD basico",
            document_type="template_catalog",
            content=(
                "El template ARDS/SDD basico genera AGENTS.md, docs/00-overview.md, "
                "docs/adr/0001-adopt-ards-sdd.md, specs/00-index.yaml, "
                "specs/templates/feature.template.yaml y scripts/check.py. "
                "Se recomienda para usuarios que necesitan una estructura inicial "
                "descargable y ordenada."
            ),
        ),
        SourceDocument(
            source_id="rule-safe-generation",
            title="Reglas de generacion segura",
            document_type="generation_rule",
            content=(
                "El agente no debe escribir archivos directamente. Debe producir "
                "una intencion estructurada con template_id, project_name, purpose "
                "y opciones. El backend valida rutas relativas, archivos permitidos "
                "y contenido antes de generar un ZIP descargable."
            ),
        ),
        SourceDocument(
            source_id="maturity-agentic",
            title="Madurez ARDS/SDD agentic",
            document_type="maturity_rule",
            content=(
                "Para un proyecto con agentes IA, incluir specs/templates/state-scenario.template.yaml, "
                "docs/tasks/README.md y una politica de POCs. Este nivel sirve cuando "
                "el usuario quiere evolucionar hacia retrievers, tools, MCP o subagentes."
            ),
        ),
    ]


def build_sample_rag_index() -> list[Document]:
    return split_documents(load_source_documents(build_sample_sst_documents()))
