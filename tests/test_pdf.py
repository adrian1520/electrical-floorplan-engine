from pathlib import Path

from pypdf import PdfReader

from electrical_floorplan_engine.models import FloorplanProject
from electrical_floorplan_engine.rendering.pdf import render_pdf


def test_render_pdf_creates_single_page_document(tmp_path: Path) -> None:
    project = FloorplanProject.model_validate(
        {
            "title": "Testowy rzut",
            "walls": [
                {
                    "id": "wall-1",
                    "start": {"x": 0, "y": 0},
                    "end": {"x": 4000, "y": 0},
                },
                {
                    "id": "wall-2",
                    "start": {"x": 4000, "y": 0},
                    "end": {"x": 4000, "y": 3000},
                },
            ],
            "symbols": [
                {"id": "light-1", "kind": "light", "position": {"x": 2000, "y": 1500}}
            ],
        }
    )
    output = render_pdf(project, tmp_path / "test.pdf")

    assert output.exists()
    assert output.stat().st_size > 500
    reader = PdfReader(str(output))
    assert len(reader.pages) == 1
    assert "Testowy rzut" in reader.pages[0].extract_text()
