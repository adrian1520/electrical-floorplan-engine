import json
from pathlib import Path

from pypdf import PdfReader

from electrical_floorplan_engine.geometry import validate_geometry
from electrical_floorplan_engine.models import FloorplanProject
from electrical_floorplan_engine.rendering.pdf import render_pdf

_ROOT = Path(__file__).resolve().parents[1]


def test_demo_project_validates_renders_and_has_no_geometry_warnings(tmp_path: Path) -> None:
    project_data = json.loads(
        (_ROOT / "examples" / "demo_project.json").read_text(encoding="utf-8")
    )
    project = FloorplanProject.model_validate(project_data)

    assert len(project.walls) == 5
    assert len(project.openings) == 3
    assert len(project.rooms) == 2
    assert validate_geometry(project) == []

    output = render_pdf(project, tmp_path / "demo.pdf")
    page = PdfReader(str(output)).pages[0]
    extracted = page.extract_text()

    assert "Salon" in extracted
    assert "Kuchnia" in extracted
    assert "D1" in extracted
    assert "D2" in extracted
    assert "W1" in extracted
    assert "Otwory: 3" in extracted
    assert "Pomieszczenia: 2" in extracted
