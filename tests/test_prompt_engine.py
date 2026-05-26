from __future__ import annotations

import pytest

from app.prompts.assembler import to_langchain_messages
from app.prompts.registry import get_prompt_definition
from app.prompts.registry import list_prompt_definitions
from app.prompts.renderer import render_prompt
from app.prompts.types import PromptDefinition
from app.prompts.types import PromptMessage
from app.prompts.types import PromptRenderRequest
from app.prompts.types import PromptVariable
from app.prompts.validators import validate_prompt_definition
from app.providers.openai_provider import build_openai_responses_options
from app.providers.types import AgentRuntimeConfig


def test_registry_loads_explicit_catalog() -> None:
    prompt_ids = {prompt.id for prompt in list_prompt_definitions()}

    assert "system.sst_base_assistant" in prompt_ids
    assert "agent.creator" in prompt_ids
    assert "task.classify_request" in prompt_ids


def test_registry_resolves_prompt_by_id_and_version() -> None:
    prompt = get_prompt_definition("system.sst_base_assistant", "1")

    assert prompt.id == "system.sst_base_assistant"
    assert prompt.version == "1"
    assert prompt.trace_policy == "metadata_only"


def test_registry_rejects_path_like_prompt_ids() -> None:
    with pytest.raises(KeyError):
        get_prompt_definition("../secrets", "1")


def test_render_prompt_applies_defaults_and_returns_metadata_only_trace() -> None:
    rendered = render_prompt(
        PromptRenderRequest(
            prompt_id="agent.creator",
            version="1",
            provider="openai",
            model="gpt-5.4-mini",
            variables={
                "user_request": "Crear un agente para resumir bitacoras.",
                "capability_id": "agent-lifecycle-and-orchestrator-boundary",
            },
        )
    )

    contents = "\n".join(message.content for message in rendered.messages)
    metadata = rendered.trace_metadata.model_dump()

    assert "SST Agent" in contents
    assert rendered.trace_metadata.prompt_id == "agent.creator"
    assert rendered.trace_metadata.provider == "openai"
    assert rendered.trace_metadata.model == "gpt-5.4-mini"
    assert rendered.trace_metadata.provider_cache_policy == "none"
    assert rendered.trace_metadata.visibility == "internal_private"
    assert rendered.trace_metadata.variable_names == (
        "agent_name",
        "capability_id",
        "user_request",
    )
    assert rendered.trace_metadata.render_ms >= 0
    assert "messages" not in metadata
    assert "Crear un agente" not in str(metadata)


def test_render_prompt_rejects_missing_required_variable() -> None:
    with pytest.raises(ValueError, match="missing variable"):
        render_prompt(
            PromptRenderRequest(
                prompt_id="task.classify_request",
                version="1",
                variables={"user_request": "Crear agente"},
            )
        )


def test_render_prompt_rejects_undeclared_variable() -> None:
    with pytest.raises(ValueError, match="undeclared variables"):
        render_prompt(
            PromptRenderRequest(
                prompt_id="task.classify_request",
                version="1",
                variables={
                    "user_request": "Crear agente",
                    "available_capabilities": "agent.create",
                    "extra": "not allowed",
                },
            )
        )


def test_render_prompt_rejects_invalid_variable_type() -> None:
    with pytest.raises(ValueError, match="must be string"):
        render_prompt(
            PromptRenderRequest(
                prompt_id="task.classify_request",
                version="1",
                variables={
                    "user_request": ["Crear agente"],
                    "available_capabilities": "agent.create",
                },
            )
        )


def test_prompt_hash_is_stable_for_same_rendered_content() -> None:
    request = PromptRenderRequest(
        prompt_id="system.sst_base_assistant",
        version="1",
        variables={"assistant_name": "Alex", "tenant_id": "tenant-1"},
    )

    first = render_prompt(request)
    second = render_prompt(request)

    assert first.trace_metadata.prompt_hash == second.trace_metadata.prompt_hash


def test_assembler_converts_to_langchain_messages() -> None:
    rendered = render_prompt(
        PromptRenderRequest(
            prompt_id="system.sst_base_assistant",
            version="1",
            variables={"assistant_name": "Alex", "tenant_id": "tenant-1"},
        )
    )

    messages = to_langchain_messages(rendered)

    assert len(messages) == 1
    assert messages[0].type == "system"


def test_validator_rejects_undeclared_placeholder() -> None:
    prompt = PromptDefinition(
        id="test.bad",
        version="1",
        messages=(PromptMessage(role="system", template="Hello {name}"),),
        variables=(
            PromptVariable(name="different_name", type="string", required=True),
        ),
    )

    with pytest.raises(ValueError, match="undeclared variables"):
        validate_prompt_definition(prompt)


def test_validator_rejects_attribute_style_placeholder() -> None:
    prompt = PromptDefinition(
        id="test.bad_attribute",
        version="1",
        messages=(PromptMessage(role="system", template="Hello {user.name}"),),
        variables=(PromptVariable(name="user", type="object", required=True),),
    )

    with pytest.raises(ValueError, match="simple variable names"):
        validate_prompt_definition(prompt)


def test_validator_rejects_format_specs() -> None:
    prompt = PromptDefinition(
        id="test.bad_format",
        version="1",
        messages=(PromptMessage(role="system", template="Score {score:.2f}"),),
        variables=(PromptVariable(name="score", type="number", required=True),),
    )

    with pytest.raises(ValueError, match="format specs"):
        validate_prompt_definition(prompt)


def test_escaped_json_literals_are_allowed() -> None:
    prompt = PromptDefinition(
        id="test.json",
        version="1",
        messages=(
            PromptMessage(
                role="system",
                template='Return JSON like {{"answer": "{answer}"}}',
            ),
        ),
        variables=(PromptVariable(name="answer", type="string", required=True),),
    )

    validate_prompt_definition(prompt)


def test_private_prompt_metadata_disables_openai_persistent_prompt_cache() -> None:
    rendered = render_prompt(
        PromptRenderRequest(
            prompt_id="system.sst_base_assistant",
            version="1",
            variables={"assistant_name": "Alex", "tenant_id": "tenant-secret"},
        )
    )
    config = AgentRuntimeConfig(model="gpt-5.5", prompt_cache_retention="auto")

    options = build_openai_responses_options(config, rendered.trace_metadata)

    assert options["model"] == "gpt-5.5"
    assert "prompt_cache_retention" not in options
