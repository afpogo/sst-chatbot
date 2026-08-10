from __future__ import annotations

from uuid import uuid4

from app.chat_runtime.port import RuntimeEvent, StreamingChatProviderPort, TurnRequest


class EchoChatRuntime:
    """Deterministic local runtime used until an approved provider is wired in."""

    def process_turn(self, request: TurnRequest):
        answer = f"SST recibió: {request.text.strip()}"
        for word in answer.split():
            yield RuntimeEvent(type="delta", text=f"{word} ")
        yield RuntimeEvent(
            type="completed",
            text=answer,
            message_id=str(uuid4()),
            correlation_id=request.correlation_id,
        )


class ProviderChatRuntime:
    """Transport-neutral runtime backed by an injected streaming provider."""

    def __init__(self, provider: StreamingChatProviderPort) -> None:
        self._provider = provider

    def process_turn(self, request: TurnRequest):
        chunks: list[str] = []
        for chunk in self._provider.stream_text(
            text=request.text,
            correlation_id=request.correlation_id,
        ):
            if not isinstance(chunk, str) or not chunk:
                continue
            chunks.append(chunk)
            yield RuntimeEvent(type="delta", text=chunk)
        yield RuntimeEvent(
            type="completed",
            text="".join(chunks),
            message_id=str(uuid4()),
            correlation_id=request.correlation_id,
        )
