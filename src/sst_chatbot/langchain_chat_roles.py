from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable, RunnableLambda


@dataclass(frozen=True)
class AssistantProfile:
    name: str
    purpose: str
    tone: str = "claro, util y profesional"


@dataclass(frozen=True)
class ChatRoleExample:
    user_message: str
    assistant_message: str


@dataclass(frozen=True)
class ChatRoleRequest:
    question: str
    profile: AssistantProfile
    examples: tuple[ChatRoleExample, ...] = ()


def build_role_messages(request: ChatRoleRequest) -> list[BaseMessage]:
    messages: list[BaseMessage] = [
        SystemMessage(
            content=(
                f"Tu nombre es {request.profile.name}. "
                f"Tu proposito es {request.profile.purpose}. "
                f"Responde con un tono {request.profile.tone}."
            )
        )
    ]

    for example in request.examples:
        messages.append(HumanMessage(content=example.user_message))
        messages.append(AIMessage(content=example.assistant_message))

    messages.append(HumanMessage(content=request.question))
    return messages


def build_chat_roles_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "Tu nombre es {assistant_name}. "
                    "Tu proposito es {assistant_purpose}. "
                    "Responde con un tono {assistant_tone}."
                ),
            ),
            MessagesPlaceholder("conversation_examples"),
            ("human", "{question}"),
        ]
    )


def build_chat_roles_input(request: ChatRoleRequest) -> dict[str, Any]:
    conversation_examples: list[BaseMessage] = []
    for example in request.examples:
        conversation_examples.append(HumanMessage(content=example.user_message))
        conversation_examples.append(AIMessage(content=example.assistant_message))

    return {
        "assistant_name": request.profile.name,
        "assistant_purpose": request.profile.purpose,
        "assistant_tone": request.profile.tone,
        "conversation_examples": conversation_examples,
        "question": request.question,
    }


def build_chat_roles_chain(chat_model: Runnable[Any, Any]) -> Runnable[dict[str, Any], str]:
    return build_chat_roles_prompt() | chat_model | StrOutputParser()


def build_mock_role_chat_model() -> Runnable[Any, AIMessage]:
    def respond(input_value: Any) -> AIMessage:
        messages = input_value.to_messages() if hasattr(input_value, "to_messages") else input_value
        text = " ".join(getattr(message, "content", "") for message in messages)

        if "nombre" in text.lower() and "alex" in text.lower():
            return AIMessage(content="Mi nombre es Alex.")

        return AIMessage(
            content=(
                "Soy Alex, un asistente especializado en explicar conceptos de IA "
                "de forma clara y practica."
            )
        )

    return RunnableLambda(respond)


def build_default_chat_role_request() -> ChatRoleRequest:
    return ChatRoleRequest(
        profile=AssistantProfile(
            name="Alex",
            purpose="ayudar a construir agentes IA para SST usando ARDS/SDD",
        ),
        examples=(
            ChatRoleExample(
                user_message="Como estas?",
                assistant_message="Estoy listo para ayudarte con agentes IA y ARDS/SDD.",
            ),
        ),
        question="Perfecto. Primero, quisiera saber cual es tu nombre.",
    )
