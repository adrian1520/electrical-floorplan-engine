import pytest
from pydantic import ValidationError

from electrical_floorplan_engine.models import FloorplanProject, RoomMM


def _base_wall() -> dict[str, object]:
    return {
        "id": "wall-1",
        "start": {"x": 0, "y": 0},
        "end": {"x": 5000, "y": 0},
        "thickness_mm": 240,
        "role": "exterior",
    }


def test_project_supports_wall_metadata_and_multiple_openings() -> None:
    project = FloorplanProject.model_validate(
        {
            "title": "Plan architektoniczny",
            "walls": [_base_wall()],
            "openings": [
                {
                    "id": "door-1",
                    "wall_id": "wall-1",
                    "kind": "door",
                    "offset_mm": 500,
                    "width_mm": 900,
                    "hinge_at": "end",
                    "swing_side": "right",
                    "label": "D1",
                },
                {
                    "id": "window-1",
                    "wall_id": "wall-1",
                    "kind": "window",
                    "offset_mm": 2200,
                    "width_mm": 1400,
                    "sill_height_mm": 900,
                },
            ],
        }
    )

    assert project.walls[0].thickness_mm == 240
    assert project.walls[0].role == "exterior"
    assert [opening.kind for opening in project.openings] == ["door", "window"]


def test_opening_must_reference_an_existing_wall() -> None:
    with pytest.raises(ValidationError, match="missing wall"):
        FloorplanProject.model_validate(
            {
                "title": "Missing host",
                "openings": [
                    {
                        "id": "door-1",
                        "wall_id": "unknown-wall",
                        "offset_mm": 0,
                        "width_mm": 800,
                    }
                ],
            }
        )


def test_opening_must_fit_inside_host_wall() -> None:
    with pytest.raises(ValidationError, match="exceeds wall"):
        FloorplanProject.model_validate(
            {
                "title": "Too wide",
                "walls": [_base_wall()],
                "openings": [
                    {
                        "id": "door-1",
                        "wall_id": "wall-1",
                        "offset_mm": 4500,
                        "width_mm": 900,
                    }
                ],
            }
        )


def test_openings_on_same_wall_must_not_overlap() -> None:
    with pytest.raises(ValidationError, match="overlap"):
        FloorplanProject.model_validate(
            {
                "title": "Overlap",
                "walls": [_base_wall()],
                "openings": [
                    {
                        "id": "door-1",
                        "wall_id": "wall-1",
                        "offset_mm": 500,
                        "width_mm": 1000,
                    },
                    {
                        "id": "window-1",
                        "wall_id": "wall-1",
                        "kind": "window",
                        "offset_mm": 1400,
                        "width_mm": 1200,
                    },
                ],
            }
        )


def test_non_window_opening_rejects_sill_height() -> None:
    with pytest.raises(ValidationError, match="only supported for window"):
        FloorplanProject.model_validate(
            {
                "title": "Sill height misuse",
                "walls": [_base_wall()],
                "openings": [
                    {
                        "id": "door-1",
                        "wall_id": "wall-1",
                        "offset_mm": 100,
                        "width_mm": 800,
                        "sill_height_mm": 0,
                    }
                ],
            }
        )


def test_room_area_centroid_and_implicit_closure() -> None:
    room = RoomMM.model_validate(
        {
            "id": "room-1",
            "name": "Salon",
            "vertices": [
                {"x": 0, "y": 0},
                {"x": 4000, "y": 0},
                {"x": 4000, "y": 3000},
                {"x": 0, "y": 3000},
            ],
        }
    )

    assert room.area_mm2 == pytest.approx(12_000_000)
    assert room.centroid.x == pytest.approx(2000)
    assert room.centroid.y == pytest.approx(1500)


def test_room_rejects_self_intersecting_boundary() -> None:
    with pytest.raises(ValidationError, match="self-intersect"):
        RoomMM.model_validate(
            {
                "id": "room-1",
                "name": "Invalid room",
                "vertices": [
                    {"x": 0, "y": 0},
                    {"x": 100, "y": 100},
                    {"x": 0, "y": 100},
                    {"x": 100, "y": 0},
                ],
            }
        )


def test_room_rejects_repeated_closing_vertex() -> None:
    with pytest.raises(ValidationError, match="implicitly closed"):
        RoomMM.model_validate(
            {
                "id": "room-1",
                "name": "Closed twice",
                "vertices": [
                    {"x": 0, "y": 0},
                    {"x": 100, "y": 0},
                    {"x": 100, "y": 100},
                    {"x": 0, "y": 100},
                    {"x": 0, "y": 0},
                ],
            }
        )


def test_ids_are_unique_across_walls_openings_rooms_and_symbols() -> None:
    with pytest.raises(ValidationError, match="unique"):
        FloorplanProject.model_validate(
            {
                "title": "Duplicate ID",
                "walls": [_base_wall()],
                "openings": [
                    {
                        "id": "wall-1",
                        "wall_id": "wall-1",
                        "offset_mm": 100,
                        "width_mm": 800,
                    }
                ],
            }
        )
