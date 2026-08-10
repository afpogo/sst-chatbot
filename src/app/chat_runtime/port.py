from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol, TypedDict


class RuntimeEvent(TypedDict, total=False):
    type: str
    text: str
    message_id: str
    correlation_id: str
    code: str


@dataclass(frozen=True)
class PrincipalContext:
    user_id: str
    account_id: str
    tenant_id: str


@dataclass(frozen=True)
class TurnRequest:
    conversation_id: str
    message_id: str
    correlation_id: str
    text: str
    principal: PrincipalContext


class ChatRuntimePort(Protocol):
    def process_turn(self, request: TurnRequest) -> Iterable[RuntimeEvent]:
        """Yield transport-neutral turn events in order."""


class StreamingChatProviderPort(Protocol):
    def stream_text(self, *, text: str, correlation_id: str) -> Iterable[str]:
        """Yield provider text without receiving the SST principal context."""
