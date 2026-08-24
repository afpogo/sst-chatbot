"""Deterministic local runtime for the CR-SST-0194 integrated smoke.

This process uses the real Auth/Bend HTTP adapters and signed service tokens.
Only the answer provider and proposal builder are deterministic test doubles.
"""

from __future__ import annotations

import argparse
import os
from http.server import ThreadingHTTPServer

from app.chat_runtime.http_server import create_handler
from app.governed_rag.fakes import RecordingGroundedAnswerProvider
from app.governed_rag.retriever import LexicalRetriever
from app.governed_rag.runtime import GovernedRagRuntime
from app.user_memory import BendUserMemoryClient
from app.user_memory import GovernedMemoryChatRuntime
from app.user_memory import MemoryProposalCandidate
from app.user_memory.contracts import MemoryTags


class DeterministicProposalBuilder:
    def build_candidate(self, *, question, answer, citations, correlation_id):
        return MemoryProposalCandidate(
            kind="fact",
            content={"statement": "La arquitectura usa memoria gobernada con citas."},
            confidence=0.95,
            validation_summary={
                "status": "validated",
                "codes": ["integrated_smoke"],
            },
            tags=MemoryTags(
                domain="sst",
                topic="architecture",
                kind="fact",
                source="chatbot",
                visibility="private",
                lifecycle="proposal",
            ),
        )


class DiagnosticBendUserMemoryClient(BendUserMemoryClient):
    def _run(self, operation, callback):
        try:
            result = callback()
            print(f"SMOKE chatbot {operation}: ok", flush=True)
            return result
        except Exception as error:
            print(f"SMOKE chatbot {operation}: {type(error).__name__}", flush=True)
            raise

    def recall_candidates(self, **kwargs):
        return self._run(
            "recall_candidates",
            lambda: super(DiagnosticBendUserMemoryClient, self).recall_candidates(**kwargs),
        )

    def audit_recall(self, **kwargs):
        return self._run(
            "audit_recall",
            lambda: super(DiagnosticBendUserMemoryClient, self).audit_recall(**kwargs),
        )

    def propose(self, **kwargs):
        return self._run(
            "propose",
            lambda: super(DiagnosticBendUserMemoryClient, self).propose(**kwargs),
        )


def build_runtime():
    client = DiagnosticBendUserMemoryClient()

    def rag_factory(source):
        return GovernedRagRuntime(
            source=source,
            retriever=LexicalRetriever(),
            provider=RecordingGroundedAnswerProvider(),
        )

    return GovernedMemoryChatRuntime(
        client=client,
        rag_factory=rag_factory,
        proposal_builder=DeterministicProposalBuilder(),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.getenv("CHAT_HTTP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("CHAT_HTTP_PORT", "8092")))
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), create_handler(runtime=build_runtime()))
    print(f"CR-SST-0194 smoke runtime listening on {args.host}:{args.port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
