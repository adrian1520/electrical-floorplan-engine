"""Validated domain models for floorplan geometry."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    def reject_zero_length(self) -> "SegmentMM":
        """Reject segments whose endpoints are identical."""
        if self.start == self.end:
            raise ValueError("Segment endpoints must be different.")
        return self


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
    walls: list[SegmentMM] = Field(default_factory=list)
    symbols: list[ElectricalSymbol] = Field(default_factory=list)
    margin_mm: float = Field(default=15.0, gt=0)
    source_image: str | None = None
    image_mm_per_pixel: float | None = Field(default=None, gt=0)
    image_origin_pixel_x: float = 0.0
    image_origin_pixel_y: float = 0.0
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_image_calibration(self) -> "FloorplanProject":
        """Require a scale whenever a raster underlay is specified."""
        if self.source_image and self.image_mm_per_pixel is None:
            raise ValueError("source_image requires image_mm_per_pixel calibration.")
        if self.image_mm_per_pixel is not None and not self.source_image:
            raise ValueError("image_mm_per_pixel requires source_image.")
        return self

    @model_validator(mode="after")
    def require_unique_ids(self) -> "FloorplanProject":
        """Require unique IDs across walls and symbols."""
        ids = [item.id for item in [*self.walls, *self.symbols]]
        if len(ids) != len(set(ids)):
            raise ValueError("Object IDs must be unique within a project.")
        return self
