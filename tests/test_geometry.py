from electrical_floorplan_engine.geometry import validate_geometry
from electrical_floorplan_engine.models import FloorplanProject


def test_geometry_warns_about_proper_wall_crossing() -> None:
    project = FloorplanProject.model_validate(
        {
            "title": "Crossing",
            "walls": [
                {"id": "w1", "start": {"x": 0, "y": 0}, "end": {"x": 100, "y": 100}},
                {"id": "w2", "start": {"x": 0, "y": 100}, "end": {"x": 100, "y": 0}},
            ],
        }
    )

    issues = validate_geometry(project)

    assert [issue.code for issue in issues] == ["crossing_walls"]
    assert issues[0].object_ids == ("w1", "w2")


def test_geometry_warns_about_collinear_wall_overlap() -> None:
    project = FloorplanProject.model_validate(
        {
            "title": "Overlap",
            "walls": [
                {"id": "w1", "start": {"x": 0, "y": 0}, "end": {"x": 100, "y": 0}},
                {"id": "w2", "start": {"x": 50, "y": 0}, "end": {"x": 150, "y": 0}},
            ],
        }
    )

    assert validate_geometry(project)[0].code == "overlapping_walls"


def test_geometry_ignores_shared_endpoints_and_t_junctions() -> None:
    project = FloorplanProject.model_validate(
        {
            "title": "Valid wall joins",
            "walls": [
                {"id": "w1", "start": {"x": 0, "y": 0}, "end": {"x": 100, "y": 0}},
                {"id": "w2", "start": {"x": 100, "y": 0}, "end": {"x": 100, "y": 100}},
                {"id": "w3", "start": {"x": 50, "y": 0}, "end": {"x": 50, "y": 40}},
            ],
        }
    )

    assert validate_geometry(project) == []


def test_geometry_warns_about_coincident_symbols() -> None:
    project = FloorplanProject.model_validate(
        {
            "title": "Duplicate symbols",
            "symbols": [
                {"id": "s1", "kind": "socket", "position": {"x": 10, "y": 10}},
                {"id": "s2", "kind": "light", "position": {"x": 10.5, "y": 10}},
            ],
        }
    )

    issues = validate_geometry(project, tolerance_mm=1.0)

    assert [issue.code for issue in issues] == ["coincident_symbols"]
