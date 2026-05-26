from __future__ import annotations

from langchain_core.messages import AIMessage
from langchain_core.messages import BaseMessage
from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage

from app.prompts.types import PromptRenderResult


def to_langchain_messages(rendered_prompt: PromptRenderResult) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for message in rendered_prompt.messages:
        if message.role == "system":
            messages.append(SystemMessage(content=message.content))
        elif message.role == "human":
            messages.append(HumanMessage(content=message.content))
        elif message.role == "assistant":
            messages.append(AIMessage(content=message.content))
        else:
            raise ValueError(f"Unsupported prompt role: {message.role}")
    return messages
