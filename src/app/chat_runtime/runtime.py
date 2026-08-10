from __future__ import annotations

from app.chat_runtime.port import RuntimeEvent, TurnRequest


class EchoChatRuntime:
    """Deterministic local runtime used until an approved provider is wired in."""

    def process_turn(self, request: TurnRequest):
        answer = f"SST recibió: {request.text.strip()}"
        for word in answer.split():
            yield RuntimeEvent(type="delta", text=f"{word} ")
        yield RuntimeEvent(
            type="completed",
            text=answer,
            message_id=f"assistant-{request.message_id}",
            correlation_id=request.correlation_id,
        )
