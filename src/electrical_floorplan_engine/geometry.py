"""Deterministic geometry diagnostics for floorplan projects."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Literal

from electrical_floorplan_engine.models import FloorplanProject, PointMM, SegmentMM

_EPSILON_MM = 1e-7


@dataclass(frozen=True, slots=True)
class GeometryIssue:
    """A non-fatal geometry finding that should be reviewed by a person."""

    code: str
    severity: Literal["warning"]
    object_ids: tuple[str, ...]
    message: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        return {
            "code": self.code,
            "severity": self.severity,
            "object_ids": list(self.object_ids),
            "message": self.message,
        }


def _cross(a: PointMM, b: PointMM, c: PointMM) -> float:
    """Twice the signed area of triangle ABC."""
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def _is_collinear(first: SegmentMM, second: SegmentMM) -> bool:
    """Return whether both endpoints of the second segment lie on the first line."""
    first_length = hypot(
        first.end.x - first.start.x,
        first.end.y - first.start.y,
    )
    return (
        abs(_cross(first.start, first.end, second.start)) / first_length <= _EPSILON_MM
        and abs(_cross(first.start, first.end, second.end)) / first_length <= _EPSILON_MM
    )


def _collinear_overlap_mm(first: SegmentMM, second: SegmentMM) -> float:
    """Return physical overlap length for collinear segments."""
    dx = first.end.x - first.start.x
    dy = first.end.y - first.start.y
    length = hypot(dx, dy)
    ux, uy = dx / length, dy / length

    def projection(point: PointMM) -> float:
        return (point.x - first.start.x) * ux + (point.y - first.start.y) * uy

    second_start, second_end = sorted((projection(second.start), projection(second.end)))
    return max(0.0, min(length, second_end) - max(0.0, second_start))


def _intersection_kind(first: SegmentMM, second: SegmentMM) -> str | None:
    """Classify material overlaps and proper interior crossings, not wall joins."""
    if _is_collinear(first, second):
        if _collinear_overlap_mm(first, second) > _EPSILON_MM:
            return "overlap"
        return None

    o1 = _cross(first.start, first.end, second.start)
    o2 = _cross(first.start, first.end, second.end)
    o3 = _cross(second.start, second.end, first.start)
    o4 = _cross(second.start, second.end, first.end)
    first_opposite = (o1 > _EPSILON_MM and o2 < -_EPSILON_MM) or (
        o1 < -_EPSILON_MM and o2 > _EPSILON_MM
    )
    second_opposite = (o3 > _EPSILON_MM and o4 < -_EPSILON_MM) or (
        o3 < -_EPSILON_MM and o4 > _EPSILON_MM
    )
    if first_opposite and second_opposite:
        return "crossing"
    # Endpoint-to-endpoint and T-junction joins are normal wall topology.
    return None


def validate_geometry(
    project: FloorplanProject, *, tolerance_mm: float = 1.0
) -> list[GeometryIssue]:
    """Find likely drafting problems without rejecting intentional geometry.

    Wall endpoint joins are accepted. Only proper interior crossings and
    collinear overlaps are reported. Symbols near the same position are
    reported as possible duplicates; findings are warnings, not automatic edits.
    """
    if tolerance_mm < 0:
        raise ValueError("tolerance_mm must be non-negative.")

    issues: list[GeometryIssue] = []
    for index, first in enumerate(project.walls):
        for second in project.walls[index + 1 :]:
            kind = _intersection_kind(first, second)
            if kind is None:
                continue
            code = "overlapping_walls" if kind == "overlap" else "crossing_walls"
            description = "overlap" if kind == "overlap" else "cross in their interiors"
            issues.append(
                GeometryIssue(
                    code=code,
                    severity="warning",
                    object_ids=(first.id, second.id),
                    message=f"Walls {first.id!r} and {second.id!r} {description}.",
                )
            )

    for index, first in enumerate(project.symbols):
        for second in project.symbols[index + 1 :]:
            distance = hypot(
                first.position.x - second.position.x,
                first.position.y - second.position.y,
            )
            if distance <= tolerance_mm:
                issues.append(
                    GeometryIssue(
                        code="coincident_symbols",
                        severity="warning",
                        object_ids=(first.id, second.id),
                        message=(
                            f"Symbols {first.id!r} and {second.id!r} are "
                            f"{distance:.3f} mm apart (tolerance {tolerance_mm:.3f} mm)."
                        ),
                    )
                )
    return issues
