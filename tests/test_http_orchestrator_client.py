from __future__ import annotations

import json
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer

import pytest

from app.orchestrator import HandoffPayload
from app.orchestrator import HttpOrchestratorClient
from app.orchestrator import OrchestratorPortError


class TokenProvider:
    def __init__(self) -> None:
        self.calls = []

    def get_token(self, audience: str, scope: str) -> str:
        self.calls.append((audience, scope))
        return "service-jwt"


def payload() -> HandoffPayload:
    return HandoffPayload(
        operation_intent_id="intent-1",
        capability_id="capability-1",
        tenant_id="tenant-1",
        idempotency_key="handoff-1",
        correlation_id="correlation-1",
    )


def receipt() -> dict[str, object]:
    return {
        "receipt_id": "receipt-1",
        "status": "accepted_for_review",
        "operation_intent_id": "intent-1",
        "capability_id": "capability-1",
        "tenant_id": "tenant-1",
        "idempotency_key": "handoff-1",
        "correlation_id": "correlation-1",
        "decision": {"accepted": True, "status": "accepted_for_review", "issues": []},
        "payload_fingerprint": "a" * 64,
    }


def test_http_handoff_uses_exact_service_grant_and_one_attempt() -> None:
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers["Content-Length"])
            requests.append({"path": self.path, "auth": self.headers["Authorization"], "body": json.loads(self.rfile.read(length))})
            body = json.dumps(receipt()).encode()
            self.send_response(202)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    tokens = TokenProvider()
    try:
        result = HttpOrchestratorClient(base_url=f"http://127.0.0.1:{server.server_port}", token_provider=tokens).submit(payload())
    finally:
        server.shutdown()
    assert result.receipt_id == "receipt-1"
    assert tokens.calls == [("sst-api", "agent-handoff:submit")]
    assert len(requests) == 1
    assert requests[0]["path"] == "/4uentes/v1/agent-handoffs"
    assert requests[0]["auth"] == "Bearer service-jwt"


def test_http_handoff_never_retries_transport_failure(monkeypatch) -> None:
    calls = []

    def fail(*_args, **_kwargs):
        calls.append(1)
        raise urllib.error.URLError("offline")

    monkeypatch.setattr("urllib.request.urlopen", fail)
    with pytest.raises(OrchestratorPortError):
        HttpOrchestratorClient(base_url="http://127.0.0.1:1", token_provider=TokenProvider()).submit(payload())
    assert len(calls) == 1
