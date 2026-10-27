"""Validated domain models for floorplan geometry."""

from __future__ import annotations

from math import hypot
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

_EPSILON_MM = 1e-7


class PointMM(BaseModel):
    """A two-dimensional point in model-space millimeters."""

    model_config = ConfigDict(frozen=True)

    x: float
    y: float


class SegmentMM(BaseModel):
    """A straight segment in model-space millimeters."""

    model_config = ConfigDict(frozen=True)

    start: PointMM
    end: PointMM
    id: str = Field(min_length=1)

    @model_validator(mode="after")
    def reject_zero_length(self) -> SegmentMM:
        """Reject segments whose endpoints are identical."""
        if self.start == self.end:
            raise ValueError("Segment endpoints must be different.")
        return self


class WallMM(SegmentMM):
    """A wall centerline with optional physical thickness and architectural role."""

    thickness_mm: float | None = Field(default=None, gt=0)
    role: Literal["exterior", "interior", "partition", "unknown"] = "unknown"


class OpeningMM(BaseModel):
    """A door, window, or passage interval measured along a host wall."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    wall_id: str = Field(min_length=1)
    kind: Literal["door", "window", "passage", "generic"] = "door"
    offset_mm: float = Field(ge=0)
    width_mm: float = Field(gt=0)
    hinge_at: Literal["start", "end"] = "start"
    swing_side: Literal["left", "right"] = "left"
    sill_height_mm: float | None = Field(default=None, ge=0)
    label: str | None = None

    @model_validator(mode="after")
    def validate_sill_height(self) -> OpeningMM:
        """Sill height is meaningful only for windows."""
        if self.sill_height_mm is not None and self.kind != "window":
            raise ValueError("sill_height_mm is only supported for window openings.")
        return self


def _cross(first: PointMM, second: PointMM, third: PointMM) -> float:
    return (second.x - first.x) * (third.y - first.y) - (
        second.y - first.y
    ) * (third.x - first.x)


def _on_segment(first: PointMM, second: PointMM, point: PointMM) -> bool:
    return (
        min(first.x, second.x) - _EPSILON_MM <= point.x <= max(first.x, second.x) + _EPSILON_MM
        and min(first.y, second.y) - _EPSILON_MM <= point.y <= max(first.y, second.y) + _EPSILON_MM
    )


def _segments_intersect(
    first_start: PointMM,
    first_end: PointMM,
    second_start: PointMM,
    second_end: PointMM,
) -> bool:
    """Return whether two closed segments intersect, including collinear contact."""
    o1 = _cross(first_start, first_end, second_start)
    o2 = _cross(first_start, first_end, second_end)
    o3 = _cross(second_start, second_end, first_start)
    o4 = _cross(second_start, second_end, first_end)

    first_opposite = (o1 > _EPSILON_MM and o2 < -_EPSILON_MM) or (
        o1 < -_EPSILON_MM and o2 > _EPSILON_MM
    )
    second_opposite = (o3 > _EPSILON_MM and o4 < -_EPSILON_MM) or (
        o3 < -_EPSILON_MM and o4 > _EPSILON_MM
    )
    if first_opposite and second_opposite:
        return True

    return (
        (abs(o1) <= _EPSILON_MM and _on_segment(first_start, first_end, second_start))
        or (abs(o2) <= _EPSILON_MM and _on_segment(first_start, first_end, second_end))
        or (abs(o3) <= _EPSILON_MM and _on_segment(second_start, second_end, first_start))
        or (abs(o4) <= _EPSILON_MM and _on_segment(second_start, second_end, first_end))
    )


class RoomMM(BaseModel):
    """A named room defined by a simple polygon in model millimeters."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=80)
    vertices: list[PointMM] = Field(min_length=3)
    label_position: PointMM | None = None

    @model_validator(mode="after")
    def validate_boundary(self) -> RoomMM:
        """Require a non-degenerate simple polygon with implicit closure."""
        vertices = self.vertices
        if vertices[0] == vertices[-1]:
            raise ValueError(
                "Room boundary is implicitly closed; do not repeat the first vertex at the end."
            )
        if len({(point.x, point.y) for point in vertices}) != len(vertices):
            raise ValueError("Room boundary must not repeat vertices.")
        for index, first in enumerate(vertices):
            second = vertices[(index + 1) % len(vertices)]
            if first == second:
                raise ValueError("Room boundary must not contain zero-length edges.")

        twice_area = sum(
            point.x * vertices[(index + 1) % len(vertices)].y
            - vertices[(index + 1) % len(vertices)].x * point.y
            for index, point in enumerate(vertices)
        )
        if abs(twice_area) <= _EPSILON_MM:
            raise ValueError("Room boundary must enclose a positive area.")

        count = len(vertices)
        for first_index in range(count):
            first_start = vertices[first_index]
            first_end = vertices[(first_index + 1) % count]
            for second_index in range(first_index + 1, count):
                # Adjacent edges share a vertex by design, including the polygon closure.
                if second_index == first_index + 1 or (
                    first_index == 0 and second_index == count - 1
                ):
                    continue
                second_start = vertices[second_index]
                second_end = vertices[(second_index + 1) % count]
                if _segments_intersect(first_start, first_end, second_start, second_end):
                    raise ValueError("Room boundary must not self-intersect.")
        return self

    @property
    def area_mm2(self) -> float:
        """Return polygon area using the shoelace formula."""
        twice_area = sum(
            point.x * self.vertices[(index + 1) % len(self.vertices)].y
            - self.vertices[(index + 1) % len(self.vertices)].x * point.y
            for index, point in enumerate(self.vertices)
        )
        return abs(twice_area) / 2

    @property
    def centroid(self) -> PointMM:
        """Return the area-weighted polygon centroid."""
        cross_terms = [
            point.x * self.vertices[(index + 1) % len(self.vertices)].y
            - self.vertices[(index + 1) % len(self.vertices)].x * point.y
            for index, point in enumerate(self.vertices)
        ]
        twice_area = sum(cross_terms)
        x = sum(
            (point.x + self.vertices[(index + 1) % len(self.vertices)].x) * cross
            for index, (point, cross) in enumerate(zip(self.vertices, cross_terms, strict=True))
        ) / (3 * twice_area)
        y = sum(
            (point.y + self.vertices[(index + 1) % len(self.vertices)].y) * cross
            for index, (point, cross) in enumerate(zip(self.vertices, cross_terms, strict=True))
        ) / (3 * twice_area)
        return PointMM(x=x, y=y)


class ElectricalSymbol(BaseModel):
    """A minimal electrical symbol marker positioned in millimeters."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    kind: Literal["socket", "switch", "light", "junction", "generic"] = "generic"
    position: PointMM
    rotation_deg: float = 0.0
    label: str | None = None


class FloorplanProject(BaseModel):
    """A project geometry ready for deterministic PDF rendering."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=160)
    units: Literal["mm"] = "mm"
    walls: list[WallMM] = Field(default_factory=list)
    openings: list[OpeningMM] = Field(default_factory=list)
    rooms: list[RoomMM] = Field(default_factory=list)
    symbols: list[ElectricalSymbol] = Field(default_factory=list)
    margin_mm: float = Field(default=15.0, gt=0)
    source_image: str | None = None
    image_mm_per_pixel: float | None = Field(default=None, gt=0)
    image_origin_pixel_x: float = 0.0
    image_origin_pixel_y: float = 0.0
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_image_calibration(self) -> FloorplanProject:
        """Require a scale whenever a raster underlay is specified."""
        if self.source_image and self.image_mm_per_pixel is None:
            raise ValueError("source_image requires image_mm_per_pixel calibration.")
        if self.image_mm_per_pixel is not None and not self.source_image:
            raise ValueError("image_mm_per_pixel requires source_image.")
        return self

    @model_validator(mode="after")
    def require_unique_ids(self) -> FloorplanProject:
        """Require unique IDs across all project objects."""
        ids = [
            item.id
            for item in [*self.walls, *self.openings, *self.rooms, *self.symbols]
        ]
        if len(ids) != len(set(ids)):
            raise ValueError("Object IDs must be unique within a project.")
        return self

    @model_validator(mode="after")
    def validate_openings(self) -> FloorplanProject:
        """Ensure opening intervals lie on host walls and do not overlap."""
        walls_by_id = {wall.id: wall for wall in self.walls}
        openings_by_wall: dict[str, list[OpeningMM]] = {}
        for opening in self.openings:
            wall = walls_by_id.get(opening.wall_id)
            if wall is None:
                raise ValueError(
                    f"Opening {opening.id!r} references missing wall {opening.wall_id!r}."
                )
            wall_length = hypot(wall.end.x - wall.start.x, wall.end.y - wall.start.y)
            if opening.offset_mm + opening.width_mm > wall_length + _EPSILON_MM:
                raise ValueError(
                    f"Opening {opening.id!r} exceeds wall {wall.id!r} length "
                    f"({wall_length:.3f} mm)."
                )
            openings_by_wall.setdefault(wall.id, []).append(opening)

        for wall_id, wall_openings in openings_by_wall.items():
            sorted_openings = sorted(wall_openings, key=lambda opening: opening.offset_mm)
            for previous, current in zip(sorted_openings, sorted_openings[1:]):
                previous_end = previous.offset_mm + previous.width_mm
                if current.offset_mm < previous_end - _EPSILON_MM:
                    raise ValueError(
                        f"Openings {previous.id!r} and {current.id!r} overlap on wall {wall_id!r}."
                    )
        return self
