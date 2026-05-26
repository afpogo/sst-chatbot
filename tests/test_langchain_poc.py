import re

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableLambda

from sst_chatbot.langchain_poc import (
    TopicSummary,
    build_capital_chain,
    build_mock_chat_model,
    build_structured_chat_model,
    build_topic_summary_chain,
)


def test_mock_chat_model_supports_invoke() -> None:
    model = build_mock_chat_model()

    result = model.invoke(
        [HumanMessage(content="Explica brevemente que es un Runnable en LangChain.")]
    )

    assert isinstance(result, AIMessage)
    assert "Runnable" in result.content


def test_mock_structured_model_returns_typed_output() -> None:
    model = build_mock_chat_model()
    structured_model = build_structured_chat_model(model)

    result = structured_model.invoke("Resumi el tema LCEL")

    assert isinstance(result, TopicSummary)
    assert result.topic == "LCEL"


def test_capital_chain_formats_prompt_and_parses_text() -> None:
    seen_prompt = {}

    def fake_model(prompt_value):
        seen_prompt["content"] = prompt_value.to_messages()[-1].content
        return AIMessage(content="La capital de Francia es Paris.")

    chain = build_capital_chain(RunnableLambda(fake_model))

    result = chain.invoke({"pais": "Francia"})

    assert result == "La capital de Francia es Paris."
    assert "capital de Francia" in seen_prompt["content"]


def test_capital_chain_supports_batch_execution() -> None:
    def fake_model(prompt_value):
        prompt_text = prompt_value.to_messages()[-1].content
        match = re.search(r"capital de (.+?)\?", prompt_text)
        country = match.group(1) if match else "desconocido"
        return AIMessage(content=f"Respuesta para {country}.")

    chain = build_capital_chain(RunnableLambda(fake_model))

    results = chain.batch(
        [
            {"pais": "Argentina"},
            {"pais": "Chile"},
        ]
    )

    assert results == [
        "Respuesta para Argentina.",
        "Respuesta para Chile.",
    ]


def test_topic_summary_chain_returns_typed_output() -> None:
    seen_prompt = {}

    def fake_structured_model(prompt_value):
        seen_prompt["content"] = prompt_value.to_messages()[-1].content
        return TopicSummary(
            topic="LCEL",
            summary="LCEL permite encadenar runnables con una sintaxis declarativa.",
            keywords=["LangChain", "LCEL", "Runnable"],
        )

    chain = build_topic_summary_chain(RunnableLambda(fake_structured_model))

    result = chain.invoke({"topic": "LCEL"})

    assert isinstance(result, TopicSummary)
    assert result.topic == "LCEL"
    assert result.keywords == ["LangChain", "LCEL", "Runnable"]
    assert "Resumi el tema LCEL" in seen_prompt["content"]
