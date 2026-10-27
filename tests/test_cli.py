import json
from pathlib import Path

from electrical_floorplan_engine.cli import main


def test_calibrate_command_writes_scale_and_origin(tmp_path: Path, capsys) -> None:
    project_path = tmp_path / "plan.json"
    project_path.write_text(
        json.dumps({"title": "Plan", "source_image": "plan.png"}),
        encoding="utf-8",
    )

    result = main(
        [
            "calibrate",
            "--project",
            str(project_path),
            "--first-pixel",
            "10,20",
            "--second-pixel",
            "110,20",
            "--length-mm",
            "2000",
        ]
    )

    output_path = tmp_path / "plan.calibrated.json"
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert result == 0
    assert saved["image_mm_per_pixel"] == 20.0
    assert saved["image_origin_pixel_x"] == 10.0
    assert saved["image_origin_pixel_y"] == 20.0
    assert "20 mm/pixel" in capsys.readouterr().out


def test_check_command_reports_warnings_and_supports_strict_mode(tmp_path: Path, capsys) -> None:
    project_path = tmp_path / "plan.json"
    project_path.write_text(
        json.dumps(
            {
                "title": "Overlap",
                "walls": [
                    {"id": "w1", "start": {"x": 0, "y": 0}, "end": {"x": 100, "y": 0}},
                    {"id": "w2", "start": {"x": 50, "y": 0}, "end": {"x": 150, "y": 0}},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = main(["check", str(project_path), "--strict"])

    assert result == 1
    assert "overlapping_walls" in capsys.readouterr().out
