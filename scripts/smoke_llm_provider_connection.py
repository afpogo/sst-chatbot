from __future__ import annotations

import json
import sys
import threading
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from app.chat_runtime.http_server import TURN_PATH, create_handler  # noqa: E402
from app.chat_runtime.runtime import ProviderChatRuntime  # noqa: E402


PROVIDER_PATH = "/v1/chat/completions"
PROVIDER_TOKEN = "smoke-provider-key"
M2M_TOKEN = "smoke-m2m-token"


class MockLlmHandler(BaseHTTPRequestHandler):
    requests: list[dict[str, Any]] = []

    def do_POST(self) -> None:  # noqa: N802
        if self.path != PROVIDER_PATH:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if self.headers.get("Authorization") != f"Bearer {PROVIDER_TOKEN}":
            self.send_error(HTTPStatus.UNAUTHORIZED)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        self.__class__.requests.append(payload)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        for content in ("respuesta ", "LLM simulada"):
            event = {"choices": [{"delta": {"content": content}}]}
            self.wfile.write(f"data: {json.dumps(event)}\n\n".encode("utf-8"))
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def log_message(self, _format: str, *_args: Any) -> None:
        return


class OpenAiCompatibleSmokeClient:
    def __init__(self, base_url: str) -> None:
        self._url = f"{base_url}{PROVIDER_PATH}"

    def stream_text(self, *, text: str, correlation_id: str):
        body = json.dumps(
            {
                "model": "smoke-model",
                "stream": True,
                "messages": [{"role": "user", "content": text}],
                "metadata": {"correlation_id": correlation_id},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self._url,
            data=body,
            headers={
                "Authorization": f"Bearer {PROVIDER_TOKEN}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            if response.headers.get_content_type() != "text/event-stream":
                raise RuntimeError("mock provider did not return an SSE stream")
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    return
                event = json.loads(data)
                content = event["choices"][0]["delta"].get("content")
                if content:
                    yield content


def _start_server(handler) -> tuple[ThreadingHTTPServer, threading.Thread]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def run_smoke() -> dict[str, Any]:
    MockLlmHandler.requests = []
    provider_server, provider_thread = _start_server(MockLlmHandler)
    provider = OpenAiCompatibleSmokeClient(f"http://127.0.0.1:{provider_server.server_port}")
    runtime = ProviderChatRuntime(provider)
    chat_server, chat_thread = _start_server(create_handler(runtime=runtime, service_token=M2M_TOKEN))
    try:
        payload = {
            "conversation_id": "smoke-conversation",
            "message_id": "smoke-message",
            "correlation_id": "smoke-correlation",
            "text": "hola proveedor",
            "principal": {
                "user_id": "smoke-user",
                "account_id": "smoke-account",
                "tenant_id": "smoke-tenant",
            },
        }
        request = urllib.request.Request(
            f"http://127.0.0.1:{chat_server.server_port}{TURN_PATH}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {M2M_TOKEN}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            events = [json.loads(line) for line in response]

        assert [event["type"] for event in events] == ["delta", "delta", "completed"]
        assert events[-1]["text"] == "respuesta LLM simulada"
        assert events[-1]["correlation_id"] == "smoke-correlation"
        assert len(MockLlmHandler.requests) == 1
        provider_request = MockLlmHandler.requests[0]
        assert provider_request["stream"] is True
        assert provider_request["messages"] == [{"role": "user", "content": "hola proveedor"}]
        serialized_provider_request = json.dumps(provider_request)
        assert "smoke-user" not in serialized_provider_request
        assert "smoke-account" not in serialized_provider_request
        assert "smoke-tenant" not in serialized_provider_request
        return {
            "ok": True,
            "provider_protocol": "openai-compatible-sse",
            "chat_protocol": "application/x-ndjson",
            "event_types": [event["type"] for event in events],
            "completed_text": events[-1]["text"],
            "principal_forwarded": False,
        }
    finally:
        chat_server.shutdown()
        chat_server.server_close()
        chat_thread.join(timeout=2)
        provider_server.shutdown()
        provider_server.server_close()
        provider_thread.join(timeout=2)


def main() -> int:
    print(json.dumps(run_smoke(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
