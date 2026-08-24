from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.chat_runtime.port import PrincipalContext, TurnRequest
from app.governed_rag.fakes import RecordingGroundedAnswerProvider
from app.governed_rag.retriever import LexicalRetriever
from app.governed_rag.runtime import GovernedRagRuntime
from app.user_memory import BendConversationMemorySource
from app.user_memory import BendUserMemoryClient
from app.user_memory import GovernedMemoryChatRuntime
from app.user_memory import MemoryProposalCandidate
from app.user_memory import UserMemoryPortError
from app.user_memory.contracts import MemoryTags


class TokenProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def get_token(self, audience: str, scope: str) -> str:
        self.calls.append((audience, scope))
        return f"token-for-{scope}"


def candidate() -> MemoryProposalCandidate:
    return MemoryProposalCandidate(
        kind="fact",
        content={"statement": "La decision final conserva memoria gobernada."},
        confidence=0.9,
        validation_summary={"status": "validated", "citationCount": 1},
        tags=MemoryTags(
            domain="sst",
            topic="architecture",
            kind="fact",
            source="chatbot",
            visibility="private",
            lifecycle="proposal",
        ),
    )


def test_http_client_uses_separate_exact_grants_and_never_sends_principal_scope() -> None:
    requests: list[dict[str, object]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(length))
            requests.append({"path": self.path, "auth": self.headers["Authorization"], "body": body})
            if self.path.endswith("recall-candidates"):
                result = {"scope": {"tenantId": "tenant-a", "userId": "user-a", "applicationId": "sst"}, "records": []}
            elif self.path.endswith("recalls"):
                result = {"id": "recall-a"}
            else:
                result = {"id": "proposal-a", "status": "needs_user_review"}
            encoded = json.dumps(result).encode()
            self.send_response(201)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    tokens = TokenProvider()
    client = BendUserMemoryClient(
        base_url=f"http://127.0.0.1:{server.server_port}",
        token_provider=tokens,
    )
    try:
        client.recall_candidates(conversation_ref="conversation-a", correlation_id="correlation-a")
        client.audit_recall(
            conversation_ref="conversation-a",
            correlation_id="correlation-a",
            retrieved_memory_ids=[],
            citation_refs=[],
        )
        receipt = client.propose(
            conversation_ref="conversation-a",
            correlation_id="correlation-a",
            idempotency_key="proposal-a",
            candidate=candidate(),
        )
    finally:
        server.shutdown()

    assert receipt.status == "needs_user_review"
    assert tokens.calls == [
        ("sst-api", "user-memory:recall"),
        ("sst-api", "user-memory:recall"),
        ("sst-api", "user-memory:propose"),
    ]
    serialized = json.dumps(requests)
    assert "tenantId" not in serialized
    assert "accountId" not in serialized
    assert "userId" not in serialized
    assert "status" not in requests[-1]["body"]["candidate"]
    assert "sourceEventIds" not in requests[-1]["body"]["candidate"]
    assert requests[-1]["auth"] == "Bearer token-for-user-memory:propose"


class FakeBendClient:
    def __init__(self, *, scope: dict[str, str] | None = None) -> None:
        self.scope = scope or {"tenantId": "tenant-a", "userId": "user-a", "applicationId": "sst"}
        self.audit_calls = []
        self.proposal_calls = []

    def recall_candidates(self, **_kwargs):
        return {
            "scope": self.scope,
            "records": [
                {
                    "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                    "kind": "fact",
                    "content": {"statement": "La arquitectura usa memoria gobernada con citas."},
                    "classification": "private",
                    "status": "active",
                    "revision": 2,
                    "visibility": {"indexable": True, "providerEligible": True},
                }
            ],
        }

    def audit_recall(self, **kwargs):
        self.audit_calls.append(kwargs)
        return {"id": "recall-a"}

    def propose(self, **kwargs):
        self.proposal_calls.append(kwargs)
        from app.user_memory import MemoryProposalReceipt

        return MemoryProposalReceipt(id="proposal-a", status="needs_user_review")


class ProposalBuilder:
    def __init__(self) -> None:
        self.calls = []

    def build_candidate(self, **kwargs):
        self.calls.append(kwargs)
        return candidate()


def turn() -> TurnRequest:
    return TurnRequest(
        conversation_id="conversation-a",
        message_id="message-a",
        correlation_id="correlation-a",
        text="Como usa memoria la arquitectura?",
        principal=PrincipalContext(user_id="user-a", account_id="account-a", tenant_id="tenant-a"),
    )


def test_composed_runtime_audits_citations_and_hands_off_pending_proposal() -> None:
    client = FakeBendClient()
    provider = RecordingGroundedAnswerProvider()
    builder = ProposalBuilder()

    def rag_factory(source):
        return GovernedRagRuntime(
            source=source,
            retriever=LexicalRetriever(),
            provider=provider,
        )

    events = list(
        GovernedMemoryChatRuntime(
            client=client,
            rag_factory=rag_factory,
            proposal_builder=builder,
        ).process_turn(turn())
    )

    assert [event["type"] for event in events] == ["memory_proposal", "delta", "completed"]
    assert events[0]["code"] == "needs_user_review"
    assert events[-1]["code"] == "grounded_answer"
    assert client.audit_calls[0]["retrieved_memory_ids"] == ["aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"]
    assert client.proposal_calls[0]["idempotency_key"].startswith("chat-memory:")
    assert builder.calls[0]["answer"] == events[-1]["text"]
    provider_payload = provider.calls[0]
    assert "principal" not in json.dumps(str(provider_payload))
    assert "tenant-a" not in json.dumps(str(provider_payload))


def test_authoritative_scope_mismatch_fails_closed_before_provider() -> None:
    client = FakeBendClient(scope={"tenantId": "tenant-b", "userId": "user-a", "applicationId": "sst"})
    provider = RecordingGroundedAnswerProvider()

    def rag_factory(source):
        return GovernedRagRuntime(source=source, retriever=LexicalRetriever(), provider=provider)

    events = list(
        GovernedMemoryChatRuntime(
            client=client,
            rag_factory=rag_factory,
            proposal_builder=ProposalBuilder(),
        ).process_turn(turn())
    )
    assert events[-1]["code"] == "source_error"
    assert events[-1]["text"] == ""
    assert provider.calls == []
    assert client.audit_calls == []
    assert client.proposal_calls == []


def test_candidate_rejects_provider_trace_and_credentials() -> None:
    with pytest.raises(ValueError):
        MemoryProposalCandidate(
            kind="fact",
            content={"statement": "Una decision valida."},
            confidence=1,
            validation_summary={"providerResponse": "raw"},
            tags=candidate().tags,
        )
    with pytest.raises(ValueError):
        MemoryProposalCandidate(
            kind="fact",
            content={"statement": "api_key=should-not-persist"},
            confidence=1,
            validation_summary={"status": "validated"},
            tags=candidate().tags,
        )


def test_source_rejects_scope_mismatch_directly() -> None:
    source = BendConversationMemorySource(
        client=FakeBendClient(scope={"tenantId": "other", "userId": "user-a", "applicationId": "sst"}),
        conversation_ref="conversation-a",
        correlation_id="correlation-a",
    )
    from app.governed_rag.contracts import RetrievalScope
    from app.governed_rag.policy import POLICY_VERSION
    from app.audience_access.contracts import DataClassification

    scope = RetrievalScope(
        tenant_id="tenant-a",
        user_id="user-a",
        application_id="sst",
        allowed_classifications=frozenset({DataClassification.PRIVATE}),
        allowed_sources=frozenset({"user_memory"}),
        policy_version=POLICY_VERSION,
    )
    with pytest.raises(UserMemoryPortError):
        tuple(source.list_candidates(scope))
