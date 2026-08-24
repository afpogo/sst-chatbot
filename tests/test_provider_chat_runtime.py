from __future__ import annotations

from uuid import UUID

from app.chat_runtime.port import PrincipalContext, TurnRequest
from app.chat_runtime.runtime import ProviderChatRuntime


class FakeStreamingProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def stream_text(self, *, text: str, correlation_id: str):
        self.calls.append({"text": text, "correlation_id": correlation_id})
        yield "respuesta "
        yield "simulada"


def test_provider_runtime_streams_without_forwarding_principal_context() -> None:
    provider = FakeStreamingProvider()
    runtime = ProviderChatRuntime(provider)
    request = TurnRequest(
        conversation_id="conversation-1",
        message_id="message-1",
        correlation_id="correlation-1",
        text="hola proveedor",
        principal=PrincipalContext(
            user_id="sensitive-user",
            account_id="sensitive-account",
            tenant_id="sensitive-tenant",
        ),
    )

    events = list(runtime.process_turn(request))

    assert provider.calls == [{"text": "hola proveedor", "correlation_id": "correlation-1"}]
    assert events[:2] == [
        {"type": "delta", "text": "respuesta "},
        {"type": "delta", "text": "simulada"},
    ]
    UUID(events[-1].pop("message_id"))
    assert events[-1] == {
        "type": "completed",
        "text": "respuesta simulada",
        "correlation_id": "correlation-1",
    }
