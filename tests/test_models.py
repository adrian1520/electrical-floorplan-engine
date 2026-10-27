import pytest
from pydantic import ValidationError

from electrical_floorplan_engine.models import FloorplanProject, PointMM, SegmentMM


def test_segment_rejects_zero_length() -> None:
    point = PointMM(x=10, y=10)
    with pytest.raises(ValidationError):
        SegmentMM(id="w1", start=point, end=point)


def test_project_rejects_duplicate_ids_across_objects() -> None:
    project_data = {
        "title": "Test",
        "walls": [
            {
                "id": "same",
                "start": {"x": 0, "y": 0},
                "end": {"x": 10, "y": 0},
            }
        ],
        "symbols": [
            {"id": "same", "kind": "light", "position": {"x": 5, "y": 5}}
        ],
    }
    with pytest.raises(ValidationError, match="unique"):
        FloorplanProject.model_validate(project_data)


def test_project_requires_scale_for_raster_underlay() -> None:
    with pytest.raises(ValidationError, match="image_mm_per_pixel"):
        FloorplanProject.model_validate(
            {"title": "Rzut", "source_image": "plan.png"}
        )
