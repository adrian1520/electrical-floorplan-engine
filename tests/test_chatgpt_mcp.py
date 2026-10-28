import base64
import hashlib
import json
from pathlib import Path

import pytest

from electrical_floorplan_engine import chatgpt_mcp

_ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/aXcAAAAASUVORK5CYII="
)


def _workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(chatgpt_mcp, "WORKSPACE", tmp_path.resolve())
    (tmp_path / "plan.png").write_bytes(_ONE_PIXEL_PNG)
    (tmp_path / "plan.json").write_text(
        json.dumps(
            {
                "title": "Rzut do edytora ChatGPT",
                "source_image": "plan.png",
                "image_mm_per_pixel": 1.0,
                "image_origin_pixel_x": 0.0,
                "image_origin_pixel_y": 0.0,
                "walls": [
                    {
                        "id": "wall-1",
                        "start": {"x": 0, "y": 0},
                        "end": {"x": 2000, "y": 0},
                        "thickness_mm": 120,
                        "role": "interior",
                    }
                ],
                "openings": [],
                "rooms": [],
                "symbols": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_mcp_editor_tool_declares_inline_ui_resource() -> None:
    specs = {tool.name: tool for tool in chatgpt_mcp._tool_specs()}
    assert specs["open_floorplan_editor"]._meta["ui"]["resourceUri"] == (
        chatgpt_mcp.RESOURCE_URI
    )
    assert "project_json" in specs["save_floorplan_project"].inputSchema["properties"]
    assert getattr(specs["save_floorplan_project"].annotations, "readOnlyHint", True) is False
    assert chatgpt_mcp._WIDGET_PATH.is_file()
    html = chatgpt_mcp._WIDGET_PATH.read_text(encoding="utf-8")
    assert 'ui/initialize' in html
    assert 'tools/call' in html
    assert "save_floorplan_project" in html


def test_mcp_workspace_lists_and_loads_project_with_raster(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    projects = chatgpt_mcp._list_projects()
    loaded = chatgpt_mcp._load_project("plan")

    assert projects[0]["id"] == "plan"
    assert projects[0]["editable"] is True
    assert loaded["revision"] == hashlib.sha256((tmp_path / "plan.json").read_bytes()).hexdigest()
    assert loaded["project"]["title"] == "Rzut do edytora ChatGPT"
    assert loaded["image_name"] == "plan.png"
    assert loaded["image_data_url"].startswith("data:image/png;base64,")


def test_mcp_save_requires_current_revision_and_valid_model(
    tmp_path: Path, monkeypatch
) -> None:
    _workspace(tmp_path, monkeypatch)
    loaded = chatgpt_mcp._load_project("plan")
    project = loaded["project"]
    project["title"] = "Rzut po edycji"

    saved = chatgpt_mcp._save_project(
        "plan",
        loaded["revision"],
        json.dumps(project),
    )

    assert saved["saved"] is True
    assert saved["revision"] == hashlib.sha256((tmp_path / "plan.json").read_bytes()).hexdigest()
    persisted = json.loads((tmp_path / "plan.json").read_text(encoding="utf-8"))
    assert persisted["title"] == "Rzut po edycji"

    with pytest.raises(chatgpt_mcp.ToolFailure, match="Konflikt zapisu"):
        chatgpt_mcp._save_project("plan", loaded["revision"], json.dumps(project))

    project["image_mm_per_pixel"] = -1
    with pytest.raises(chatgpt_mcp.ToolFailure, match="nieprawidłowe"):
        chatgpt_mcp._save_project("plan", saved["revision"], json.dumps(project))


def test_mcp_rejects_paths_outside_workspace(
    tmp_path: Path, monkeypatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    secret_image = tmp_path / "outside.png"
    secret_image.write_bytes(_ONE_PIXEL_PNG)
    (workspace / "plan.json").write_text(
        json.dumps(
            {
                "title": "Zewnętrzny obraz",
                "source_image": str(secret_image),
                "image_mm_per_pixel": 1.0,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(chatgpt_mcp, "WORKSPACE", workspace.resolve())

    with pytest.raises(chatgpt_mcp.ToolFailure, match="workspace"):
        chatgpt_mcp._load_project("plan")


def test_mcp_geometry_validation_returns_warnings(
    tmp_path: Path, monkeypatch
) -> None:
    _workspace(tmp_path, monkeypatch)
    project = json.loads((tmp_path / "plan.json").read_text(encoding="utf-8"))
    project["walls"].append(
        {
            "id": "wall-2",
            "start": {"x": 1000, "y": -500},
            "end": {"x": 1000, "y": 500},
            "thickness_mm": 100,
            "role": "interior",
        }
    )

    result = chatgpt_mcp._validate_project(json.dumps(project))

    assert result["valid"] is True
    assert result["issues"][0]["code"] == "crossing_walls"
