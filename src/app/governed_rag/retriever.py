from __future__ import annotations

import re

from app.governed_rag.contracts import AuthorizedChunk
from app.governed_rag.contracts import RankedChunk


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2
    }


class LexicalRetriever:
    """Deterministic local retriever; it has no authorization responsibility."""

    def retrieve(
        self,
        *,
        query: str,
        chunks: tuple[AuthorizedChunk, ...],
        limit: int,
        minimum_score: float,
    ) -> tuple[RankedChunk, ...]:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        if minimum_score <= 0:
            raise ValueError("minimum_score must be greater than zero")
        query_tokens = _tokens(query)
        ranked: list[RankedChunk] = []
        for chunk in chunks:
            score = float(
                len(query_tokens.intersection(_tokens(f"{chunk.title} {chunk.content}")))
            )
            if score >= minimum_score:
                ranked.append(RankedChunk(chunk=chunk, score=score))
        ranked.sort(key=lambda item: (-item.score, item.chunk.chunk_id))
        return tuple(ranked[:limit])
