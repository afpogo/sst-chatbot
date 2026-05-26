from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from sst_chatbot.langchain_chat_roles import (
    AssistantProfile,
    ChatRoleExample,
    ChatRoleRequest,
    build_chat_roles_chain,
    build_chat_roles_input,
    build_default_chat_role_request,
    build_mock_role_chat_model,
    build_role_messages,
)


def test_build_role_messages_preserves_chat_roles_order() -> None:
    request = ChatRoleRequest(
        profile=AssistantProfile(name="Alex", purpose="ayudar con SST"),
        examples=(
            ChatRoleExample(
                user_message="Hola",
                assistant_message="Hola, listo para ayudar.",
            ),
        ),
        question="Cual es tu nombre?",
    )

    messages = build_role_messages(request)

    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert isinstance(messages[2], AIMessage)
    assert isinstance(messages[3], HumanMessage)
    assert "Alex" in messages[0].content


def test_build_chat_roles_input_maps_examples_to_messages() -> None:
    request = build_default_chat_role_request()

    chain_input = build_chat_roles_input(request)

    assert chain_input["assistant_name"] == "Alex"
    assert len(chain_input["conversation_examples"]) == 2
    assert chain_input["question"] == request.question


def test_chat_roles_chain_returns_mock_response() -> None:
    request = build_default_chat_role_request()
    chain = build_chat_roles_chain(build_mock_role_chat_model())

    result = chain.invoke(build_chat_roles_input(request))

    assert result == "Mi nombre es Alex."
