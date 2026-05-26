from zipfile import ZipFile
from io import BytesIO

import pytest

from sst_chatbot.ards_generator import (
    ArdsFile,
    UserWorkspaceRequest,
    build_ards_sdd_bundle,
    build_user_workspace_layout,
    build_workspace_id,
    slugify_project_name,
)


def test_build_ards_sdd_bundle_generates_required_structure() -> None:
    bundle = build_ards_sdd_bundle(
        project_name="SST Demo",
        purpose="Generate an internal ARDS/SDD structure.",
    )

    files = bundle.as_dict()

    assert "AGENTS.md" in files
    assert "docs/00-overview.md" in files
    assert "docs/adr/0001-adopt-ards-sdd.md" in files
    assert "specs/00-index.yaml" in files
    assert "scripts/check.py" in files
    assert "repository: sst-demo" in files["specs/00-index.yaml"]


def test_build_ards_sdd_bundle_can_be_downloaded_as_zip() -> None:
    bundle = build_ards_sdd_bundle(
        project_name="SST Demo",
        purpose="Generate an internal ARDS/SDD structure.",
    )

    archive_bytes = bundle.to_zip_bytes()

    with ZipFile(BytesIO(archive_bytes)) as archive:
        names = archive.namelist()

    assert "AGENTS.md" in names
    assert "specs/templates/state-scenario.template.yaml" in names


def test_ards_file_rejects_paths_outside_bundle() -> None:
    with pytest.raises(ValueError):
        ArdsFile("../secrets.env", "bad")

    with pytest.raises(ValueError):
        ArdsFile("C:/tmp/secrets.env", "bad")


def test_slugify_project_name_has_stable_fallback() -> None:
    assert slugify_project_name("SST Demo!") == "sst-demo"
    assert slugify_project_name("   ") == "ards-project"


def test_build_workspace_id_is_stable_and_scoped() -> None:
    workspace_id = build_workspace_id(
        account_id="Account 1",
        user_id="User 99",
        project_name="Mi Proyecto SST",
    )

    assert workspace_id == "account-1-user-99-mi-proyecto-sst"


def test_build_user_workspace_layout_adds_metadata_manifest() -> None:
    layout = build_user_workspace_layout(
        UserWorkspaceRequest(
            account_id="account-1",
            user_id="user-1",
            display_name="User One",
            project_name="SST Demo",
            purpose="Create generated ARDS/SDD for a user.",
            storage_mode="hybrid",
        )
    )

    files = layout.bundle.as_dict()

    assert layout.root_path == "workspaces/account-1-user-1-sst-demo"
    assert ".sst/workspace.yaml" in files
    assert "storage_mode: hybrid" in files[".sst/workspace.yaml"]
    assert "workspaces/account-1-user-1-sst-demo/AGENTS.md" in layout.logical_paths()


def test_build_user_workspace_layout_rejects_unknown_storage_mode() -> None:
    with pytest.raises(ValueError):
        build_user_workspace_layout(
            UserWorkspaceRequest(
                account_id="account-1",
                user_id="user-1",
                display_name="User One",
                project_name="SST Demo",
                purpose="Create generated ARDS/SDD for a user.",
                storage_mode="remote",
            )
        )
