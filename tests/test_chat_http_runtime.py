from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from uuid import UUID
from http.server import ThreadingHTTPServer

from app.chat_runtime.http_server import TURN_PATH, create_handler


def _request(port: int, *, token: str = "test-m2m", payload=None):
    body = json.dumps(payload or {}).encode()
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{TURN_PATH}",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    return urllib.request.urlopen(request, timeout=2)


def _payload():
    return {
        "conversation_id": "conversation-1",
        "message_id": "message-1",
        "correlation_id": "correlation-1",
        "text": "hola",
        "principal": {"user_id": "user-1", "account_id": "account-1", "tenant_id": "tenant-1"},
    }


def test_turn_streams_delta_then_completed():
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(service_token="test-m2m"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with _request(server.server_port, payload=_payload()) as response:
            events = [json.loads(line) for line in response]
        assert response.headers["Content-Type"] == "application/x-ndjson"
        assert events[0]["type"] == "delta"
        UUID(events[-1].pop("message_id"))
        assert events[-1] == {
            "type": "completed",
            "text": "SST recibió: hola",
            "correlation_id": "correlation-1",
        }
    finally:
        server.shutdown()


def test_turn_rejects_invalid_service_token():
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(service_token="test-m2m"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        try:
            _request(server.server_port, token="wrong", payload=_payload())
            assert False, "request must fail"
        except urllib.error.HTTPError as error:
            assert error.code == 401
    finally:
        server.shutdown()


def test_turn_rejects_unvalidated_principal():
    payload = _payload()
    payload["principal"].pop("tenant_id")
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(service_token="test-m2m"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        try:
            _request(server.server_port, payload=payload)
            assert False, "request must fail"
        except urllib.error.HTTPError as error:
            assert error.code == 400
    finally:
        server.shutdown()


def test_turn_uses_injected_service_jwt_verifier():
    tokens = []

    def verify(token):
        tokens.append(token)
        if token != "signed-service-jwt":
            from app.service_auth import ServiceCredentialError
            raise ServiceCredentialError("invalid")

    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(token_verifier=verify))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with _request(server.server_port, token="signed-service-jwt", payload=_payload()) as response:
            assert response.status == 200
    finally:
        server.shutdown()
    assert tokens == ["signed-service-jwt"]
