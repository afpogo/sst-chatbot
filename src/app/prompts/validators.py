from __future__ import annotations

from string import Formatter
from typing import Any

from app.prompts.types import PromptDefinition
from app.prompts.types import PromptVariable

_FORMATTER = Formatter()


def extract_placeholders(template: str) -> set[str]:
    placeholders: set[str] = set()
    for _, field_name, format_spec, conversion in _FORMATTER.parse(template):
        if not field_name:
            continue
        _validate_field_name(field_name, format_spec, conversion)
        placeholders.add(field_name)
    return placeholders


def _validate_field_name(
    field_name: str,
    format_spec: str | None,
    conversion: str | None,
) -> None:
    if any(token in field_name for token in (".", "[", "]")):
        raise ValueError(
            "Prompt placeholders must be simple variable names without attribute "
            f"or index access: {field_name}"
        )
    if format_spec:
        raise ValueError(
            f"Prompt placeholder format specs are not supported: {field_name}"
        )
    if conversion:
        raise ValueError(
            f"Prompt placeholder conversions are not supported: {field_name}"
        )


def validate_prompt_definition(prompt: PromptDefinition) -> None:
    if not prompt.messages:
        raise ValueError(f"Prompt {prompt.id}:{prompt.version} must define messages.")

    declared_names = {variable.name for variable in prompt.variables}
    if len(declared_names) != len(prompt.variables):
        raise ValueError(f"Prompt {prompt.id}:{prompt.version} has duplicate variables.")

    placeholders: set[str] = set()
    for message in prompt.messages:
        placeholders.update(extract_placeholders(message.template))

    missing_declarations = sorted(placeholders - declared_names)
    if missing_declarations:
        raise ValueError(
            f"Prompt {prompt.id}:{prompt.version} uses undeclared variables: "
            + ", ".join(missing_declarations)
        )

    required_unused = sorted(
        variable.name
        for variable in prompt.variables
        if variable.required and variable.default is None and variable.name not in placeholders
    )
    if required_unused:
        raise ValueError(
            f"Prompt {prompt.id}:{prompt.version} declares unused required variables: "
            + ", ".join(required_unused)
        )


def validate_render_variables(
    prompt: PromptDefinition,
    variables: dict[str, Any],
) -> dict[str, Any]:
    variable_contracts = {variable.name: variable for variable in prompt.variables}
    unknown_variables = sorted(set(variables) - set(variable_contracts))
    if unknown_variables:
        raise ValueError(
            f"Prompt {prompt.id}:{prompt.version} received undeclared variables: "
            + ", ".join(unknown_variables)
        )

    resolved: dict[str, Any] = {}
    for name, contract in variable_contracts.items():
        if name in variables:
            value = variables[name]
        elif contract.default is not None:
            value = contract.default
        elif contract.required:
            raise ValueError(
                f"Prompt {prompt.id}:{prompt.version} is missing variable: {name}"
            )
        else:
            value = ""

        _validate_type(contract, value)
        resolved[name] = value

    return resolved


def _validate_type(contract: PromptVariable, value: Any) -> None:
    expected_type = contract.type
    valid = (
        (expected_type == "string" and isinstance(value, str))
        or (
            expected_type == "integer"
            and isinstance(value, int)
            and not isinstance(value, bool)
        )
        or (
            expected_type == "number"
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        )
        or (expected_type == "boolean" and isinstance(value, bool))
        or (expected_type == "list" and isinstance(value, list))
        or (expected_type == "object" and isinstance(value, dict))
    )
    if not valid:
        raise ValueError(
            f"Variable {contract.name} must be {expected_type}, "
            f"got {type(value).__name__}."
        )
