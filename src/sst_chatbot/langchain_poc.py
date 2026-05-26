from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from sst_chatbot.config import get_default_chat_model


class TopicSummary(BaseModel):
    """Structured response used by the notebook POC."""

    topic: str = Field(description="Tema principal identificado en la consulta.")
    summary: str = Field(description="Resumen breve en espanol.")
    keywords: list[str] = Field(
        description="Lista corta de palabras clave relacionadas con el tema."
    )


def _extract_text(input_value: Any) -> str:
    if hasattr(input_value, "to_messages"):
        messages = input_value.to_messages()
    elif isinstance(input_value, list):
        messages = input_value
    else:
        return str(input_value)

    parts: list[str] = []
    for message in messages:
        content = getattr(message, "content", "")
        if isinstance(content, str):
            parts.append(content)
        else:
            parts.append(str(content))
    return " ".join(parts)


def _mock_chat_response(input_value: Any) -> AIMessage:
    text = _extract_text(input_value)
    lowered = text.lower()

    if "capital de" in lowered:
        match = re.search(r"capital de ([^?.!]+)", lowered)
        country = match.group(1).strip() if match else "ese pais"
        capitals = {
            "francia": "Paris",
            "argentina": "Buenos Aires",
            "uruguay": "Montevideo",
            "chile": "Santiago",
        }
        capital = capitals.get(country, "No lo se en modo mock")
        return AIMessage(content=f"La capital de {country.title()} es {capital}.")

    if "lcel" in lowered:
        return AIMessage(
            content=(
                "LCEL permite encadenar runnables con el operador pipe. "
                "Eso hace mas declarativa la composicion de prompts, modelos y parsers."
            )
        )

    if "runnable" in lowered:
        return AIMessage(
            content=(
                "Un Runnable es una unidad estandar de trabajo en LangChain. "
                "Se puede invocar con invoke, batch o stream y combinar con otros componentes."
            )
        )

    return AIMessage(
        content="Respuesta mock generada para practicar Runnable y LCEL sin usar la API."
    )


def _mock_structured_response(input_value: Any) -> TopicSummary:
    text = _extract_text(input_value)
    topic = "LCEL" if "lcel" in text.lower() else "LangChain"
    return TopicSummary(
        topic=topic,
        summary=(
            "LCEL permite definir cadenas declarativas y reutilizables entre prompts, "
            "modelos y parsers."
        ),
        keywords=["LangChain", "LCEL", "Runnable"],
    )


def build_chat_model(
    model_name: str | None = None,
    temperature: float = 0.0,
) -> ChatOpenAI:
    return ChatOpenAI(
        model=model_name or get_default_chat_model(),
        temperature=temperature,
    )


def build_mock_chat_model() -> Runnable[Any, AIMessage]:
    return RunnableLambda(_mock_chat_response)


def build_capital_chain(chat_model: Runnable[Any, Any]) -> Runnable[dict[str, str], str]:
    prompt = ChatPromptTemplate.from_template(
        "Cual es la capital de {pais}? Responde en una sola oracion."
    )
    return prompt | chat_model | StrOutputParser()


def build_structured_chat_model(
    chat_model: Runnable[Any, Any],
) -> Runnable[Any, TopicSummary]:
    if hasattr(chat_model, "with_structured_output"):
        return chat_model.with_structured_output(TopicSummary)
    return RunnableLambda(_mock_structured_response)


def build_topic_summary_chain(
    structured_model: Runnable[Any, TopicSummary],
) -> Runnable[dict[str, str], TopicSummary]:
    prompt = ChatPromptTemplate.from_template(
        "Resumi el tema {topic} en 2 oraciones y devolve hasta 3 palabras clave."
    )
    return prompt | structured_model
