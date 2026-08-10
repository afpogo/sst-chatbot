from __future__ import annotations

import argparse
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from app.chat_runtime.port import PrincipalContext, TurnRequest
from app.chat_runtime.runtime import EchoChatRuntime
from app.service_auth import JwksServiceTokenVerifier
from app.service_auth import ServiceCredentialError

TURN_PATH = "/internal/v1/chat/turns"


def _turn_request(payload: dict[str, Any]) -> TurnRequest:
    principal = payload.get("principal") or {}
    required = {
        "conversation_id": payload.get("conversation_id"),
        "message_id": payload.get("message_id"),
        "correlation_id": payload.get("correlation_id"),
        "text": payload.get("text"),
        "user_id": principal.get("user_id"),
        "account_id": principal.get("account_id"),
        "tenant_id": principal.get("tenant_id"),
    }
    missing = [name for name, value in required.items() if not isinstance(value, str) or not value.strip()]
    if missing:
        raise ValueError(f"missing or invalid fields: {', '.join(missing)}")
    if len(required["text"].encode("utf-8")) > 16_384:
        raise ValueError("text exceeds 16384 bytes")
    return TurnRequest(
        conversation_id=required["conversation_id"],
        message_id=required["message_id"],
        correlation_id=required["correlation_id"],
        text=required["text"],
        principal=PrincipalContext(
            user_id=required["user_id"],
            account_id=required["account_id"],
            tenant_id=required["tenant_id"],
        ),
    )


def create_handler(runtime=None, service_token: str | None = None, token_verifier=None):
    selected_runtime = runtime or EchoChatRuntime()
    if token_verifier is not None:
        selected_verifier = token_verifier
    elif service_token is not None:
        def selected_verifier(token: str) -> None:
            if token != service_token:
                raise ServiceCredentialError("invalid service token")
    else:
        selected_verifier = JwksServiceTokenVerifier.from_env().verify

    class ChatHandler(BaseHTTPRequestHandler):
        server_version = "sst-chatbot/1"

        def _json_error(self, status: HTTPStatus, code: str, message: str) -> None:
            body = json.dumps({"error": {"code": code, "message": message}}).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != TURN_PATH:
                self._json_error(HTTPStatus.NOT_FOUND, "not_found", "Route not found")
                return
            auth = self.headers.get("Authorization", "")
            token = auth[7:] if auth.startswith("Bearer ") else ""
            try:
                if not token:
                    raise ServiceCredentialError("missing service token")
                selected_verifier(token)
            except ServiceCredentialError:
                self._json_error(HTTPStatus.UNAUTHORIZED, "unauthorized", "Invalid service credential")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 32_768:
                    raise ValueError("request body size is invalid")
                request = _turn_request(json.loads(self.rfile.read(length)))
            except (ValueError, json.JSONDecodeError) as exc:
                self._json_error(HTTPStatus.BAD_REQUEST, "invalid_request", str(exc))
                return

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                for event in selected_runtime.process_turn(request):
                    self.wfile.write(json.dumps(event, ensure_ascii=False).encode("utf-8") + b"\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception:
                event = {"type": "error", "code": "runtime_error", "correlation_id": request.correlation_id}
                self.wfile.write(json.dumps(event).encode() + b"\n")

        def log_message(self, _format: str, *_args: Any) -> None:
            return

    return ChatHandler


def serve(host: str, port: int, service_token: str | None = None) -> None:
    server = ThreadingHTTPServer((host, port), create_handler(service_token=service_token))
    print(f"sst-chatbot HTTP runtime listening on http://{host}:{port}{TURN_PATH}", flush=True)
    server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.getenv("CHAT_HTTP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("CHAT_HTTP_PORT", "8091")))
    args = parser.parse_args()
    serve(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
