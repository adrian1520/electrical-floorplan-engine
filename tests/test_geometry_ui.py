import base64
import json
from pathlib import Path

import pytest

from electrical_floorplan_engine.cli import main
from electrical_floorplan_engine.geometry_ui import create_geometry_ui

_ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/aXcAAAAASUVORK5CYII="
)


def _make_project(tmp_path: Path, *, calibrated: bool = True) -> Path:
    image_path = tmp_path / "plan.png"
    image_path.write_bytes(_ONE_PIXEL_PNG)
    project_path = tmp_path / "plan.calibrated.json"
    data = {
        "title": "Rzut testowy",
        "source_image": "plan.png",
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
    }
    if calibrated:
        data.update(
            {
                "image_mm_per_pixel": 1.0,
                "image_origin_pixel_x": 0,
                "image_origin_pixel_y": 0,
            }
        )
    project_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return project_path


def test_geometry_ui_embeds_calibrated_project_and_source_image(tmp_path: Path) -> None:
    project_path = _make_project(tmp_path)

    output = create_geometry_ui(project_path)
    html = output.read_text(encoding="utf-8")

    assert output == tmp_path / "plan.calibrated.geometry.html"
    assert "data:image/png;base64," in html
    assert 'data-tool="wall"' in html
    assert 'data-tool="room"' in html
    assert 'data-tool="opening"' in html
    assert "function validateProject()" in html
    assert "function validRoom(vertices)" in html
    assert "function saveUndo()" in html
    assert "const sourceName = decodeBase64(SOURCE_NAME_BASE64);" in html
    assert "__IMAGE_DATA_URI__" not in html
    assert "__PROJECT_BASE64__" not in html
    assert "__SOURCE_NAME_BASE64__" not in html
    assert "fetch(" not in html
    assert "https://" not in html


def test_geometry_ui_requires_source_image_and_calibration(tmp_path: Path) -> None:
    project_path = tmp_path / "uncalibrated.json"
    project_path.write_text(json.dumps({"title": "Bez obrazu"}), encoding="utf-8")

    with pytest.raises(ValueError, match="source_image"):
        create_geometry_ui(project_path)


def test_geometry_ui_reports_missing_raster(tmp_path: Path) -> None:
    project_path = tmp_path / "missing.json"
    project_path.write_text(
        json.dumps(
            {
                "title": "Brak obrazu",
                "source_image": "missing.png",
                "image_mm_per_pixel": 1.0,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="missing.png"):
        create_geometry_ui(project_path)


def test_edit_geometry_cli_writes_html_to_requested_path(tmp_path: Path, capsys) -> None:
    project_path = _make_project(tmp_path)
    output_path = tmp_path / "tools" / "geometry.html"

    result = main(
        [
            "edit-geometry",
            "--project",
            str(project_path),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    assert output_path.is_file()
    assert str(output_path) in capsys.readouterr().out
