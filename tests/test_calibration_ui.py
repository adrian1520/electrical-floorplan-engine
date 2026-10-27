import base64
import json
from pathlib import Path

import pytest

from electrical_floorplan_engine.calibration_ui import create_calibration_ui
from electrical_floorplan_engine.cli import main

_ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/aXcAAAAASUVORK5CYII="
)


def _make_project(tmp_path: Path) -> Path:
    image_path = tmp_path / "plan.png"
    image_path.write_bytes(_ONE_PIXEL_PNG)
    project_path = tmp_path / "plan.json"
    project_path.write_text(
        json.dumps(
            {
                "title": "Rzut testowy",
                "source_image": "plan.png",
                "walls": [],
                "symbols": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return project_path


def test_calibration_ui_embeds_image_and_project_without_network_assets(tmp_path: Path) -> None:
    project_path = _make_project(tmp_path)

    output = create_calibration_ui(project_path)
    html = output.read_text(encoding="utf-8")

    assert output == tmp_path / "plan.calibration.html"
    assert "data:image/png;base64," in html
    assert 'id="known-length"' in html
    assert 'id="overlay"' in html
    assert "Pobierz skalibrowany JSON" in html
    assert "fetch(" not in html
    assert "https://" not in html


def test_calibration_ui_requires_a_source_image(tmp_path: Path) -> None:
    project_path = tmp_path / "invalid.json"
    project_path.write_text('{"title": "Bez obrazu"}', encoding="utf-8")

    with pytest.raises(ValueError, match="source_image"):
        create_calibration_ui(project_path)


def test_calibration_ui_reports_missing_source_image(tmp_path: Path) -> None:
    project_path = tmp_path / "invalid.json"
    project_path.write_text(
        json.dumps({"title": "Brak obrazu", "source_image": "missing.png"}),
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="missing.png"):
        create_calibration_ui(project_path)


def test_calibrate_ui_cli_writes_html_to_requested_path(tmp_path: Path, capsys) -> None:
    project_path = _make_project(tmp_path)
    output_path = tmp_path / "tools" / "calibration.html"

    result = main(
        [
            "calibrate-ui",
            "--project",
            str(project_path),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    assert output_path.is_file()
    assert str(output_path) in capsys.readouterr().out
