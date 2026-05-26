from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
import re
from zipfile import ZIP_DEFLATED, ZipFile


def slugify_project_name(project_name: str) -> str:
    normalized = project_name.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = normalized.strip("-")
    return normalized or "ards-project"


def validate_relative_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    if not normalized:
        raise ValueError("Path cannot be empty.")
    if ":" in normalized:
        raise ValueError(f"Path cannot contain a drive or scheme: {path}")

    pure_path = PurePosixPath(normalized)
    if pure_path.is_absolute() or ".." in pure_path.parts:
        raise ValueError(f"Path must stay inside the generated bundle: {path}")

    return pure_path.as_posix()


@dataclass(frozen=True)
class ArdsFile:
    path: str
    content: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", validate_relative_path(self.path))


@dataclass(frozen=True)
class ArdsBundle:
    project_name: str
    files: tuple[ArdsFile, ...]

    def as_dict(self) -> dict[str, str]:
        return {file.path: file.content for file in self.files}

    def to_zip_bytes(self) -> bytes:
        buffer = BytesIO()
        with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
            for file in self.files:
                archive.writestr(file.path, file.content)
        return buffer.getvalue()


@dataclass(frozen=True)
class UserWorkspaceRequest:
    user_id: str
    account_id: str
    display_name: str
    project_name: str
    purpose: str
    storage_mode: str = "logical"


@dataclass(frozen=True)
class UserWorkspaceLayout:
    workspace_id: str
    root_path: str
    storage_mode: str
    bundle: ArdsBundle

    def logical_paths(self) -> list[str]:
        return [f"{self.root_path}/{file.path}" for file in self.bundle.files]


def build_workspace_id(account_id: str, user_id: str, project_name: str) -> str:
    account_slug = slugify_project_name(account_id)
    user_slug = slugify_project_name(user_id)
    project_slug = slugify_project_name(project_name)
    return f"{account_slug}-{user_slug}-{project_slug}"


def build_user_workspace_layout(
    request: UserWorkspaceRequest,
) -> UserWorkspaceLayout:
    if request.storage_mode not in {"logical", "physical", "hybrid"}:
        raise ValueError("storage_mode must be logical, physical, or hybrid")

    workspace_id = build_workspace_id(
        request.account_id,
        request.user_id,
        request.project_name,
    )
    root_path = validate_relative_path(f"workspaces/{workspace_id}")
    bundle = build_ards_sdd_bundle(
        project_name=request.project_name,
        purpose=request.purpose,
    )

    workspace_files = list(bundle.files)
    workspace_files.append(
        ArdsFile(
            ".sst/workspace.yaml",
            f"""version: 1
kind: sst_user_workspace
workspace_id: {workspace_id}
account_id: {request.account_id}
user_id: {request.user_id}
display_name: {request.display_name}
storage_mode: {request.storage_mode}
generated_root: {root_path}
""",
        )
    )

    return UserWorkspaceLayout(
        workspace_id=workspace_id,
        root_path=root_path,
        storage_mode=request.storage_mode,
        bundle=ArdsBundle(
            project_name=request.project_name,
            files=tuple(workspace_files),
        ),
    )


def build_ards_sdd_bundle(
    project_name: str,
    purpose: str,
    include_state_template: bool = True,
) -> ArdsBundle:
    slug = slugify_project_name(project_name)
    files = [
        ArdsFile(
            "AGENTS.md",
            f"""# {project_name} Agent Guide

## Purpose
{purpose}

## Operating Rules
- Keep reusable implementation in `src/`.
- Keep durable specs in `specs/`.
- Keep human-readable decisions and context in `docs/`.
- Do not commit secrets or generated runtime state.
""",
        ),
        ArdsFile(
            "docs/00-overview.md",
            f"""# {project_name} Overview

## Purpose
{purpose}

## ARDS/SDD Layout
- `AGENTS.md`: operational guide.
- `docs/`: human-readable context and decisions.
- `specs/`: source of truth for requirements and contracts.
- `scripts/`: repeatable validation commands.
""",
        ),
        ArdsFile(
            "docs/adr/0001-adopt-ards-sdd.md",
            f"""# ADR 0001: Adopt ARDS/SDD

## Status
Accepted

## Context
{project_name} needs durable context for humans and AI agents.

## Decision
Use ARDS/SDD as the repository structure.
""",
        ),
        ArdsFile(
            "specs/00-index.yaml",
            f"""version: 1
kind: ards_sdd_index
repository: {slug}
description: {purpose}
entries:
  features: []
  states: []
templates:
  - path: specs/templates/feature.template.yaml
""",
        ),
        ArdsFile(
            "specs/templates/feature.template.yaml",
            """version: 1
kind: feature
id: feature-id
status: draft
title: Feature title
goal: Feature goal.
requirements: []
acceptance_criteria: []
validation:
  commands: []
""",
        ),
        ArdsFile(
            "scripts/check.py",
            """from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    required_paths = [
        "AGENTS.md",
        "docs/00-overview.md",
        "specs/00-index.yaml",
    ]
    missing = [path for path in required_paths if not (ROOT_DIR / path).exists()]
    if missing:
        print("Missing required paths:")
        for path in missing:
            print(f"- {path}")
        return 1
    print("ARDS/SDD structure check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
""",
        ),
    ]

    if include_state_template:
        files.append(
            ArdsFile(
                "specs/templates/state-scenario.template.yaml",
                """version: 1
kind: state_scenario
state_id: state-id
status: draft
execution_mode: parallel
depends_on: []
inputs:
  human: []
  agent: []
  script_event: []
workflow: []
transitions:
  ready:
    when: Preconditions are satisfied.
  blocked:
    when: Required input is missing.
  done:
    when: Acceptance criteria pass.
""",
            )
        )

    return ArdsBundle(project_name=project_name, files=tuple(files))
