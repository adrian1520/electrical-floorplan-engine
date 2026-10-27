"""Pixel-to-millimeter calibration helpers."""

from __future__ import annotations

from math import hypot, isfinite

from pydantic import BaseModel, ConfigDict, Field, model_validator

from electrical_floorplan_engine.models import PointMM


class PixelPoint(BaseModel):
    """A point in source-image pixel coordinates."""

    model_config = ConfigDict(frozen=True)

    x: float
    y: float


class ScaleCalibration(BaseModel):
    """Uniform scale calibration from a known image segment."""

    model_config = ConfigDict(frozen=True)

    first_pixel: PixelPoint
    second_pixel: PixelPoint
    known_length_mm: float = Field(gt=0)
    origin_pixel: PixelPoint = Field(default_factory=lambda: PixelPoint(x=0, y=0))

    @model_validator(mode="after")
    def validate_reference_segment(self) -> ScaleCalibration:
        """Ensure the reference segment and its values are valid."""
        pixel_length = hypot(
            self.second_pixel.x - self.first_pixel.x,
            self.second_pixel.y - self.first_pixel.y,
        )
        if not isfinite(pixel_length) or pixel_length <= 0:
            raise ValueError("Reference points must define a positive pixel length.")
        return self

    @property
    def mm_per_pixel(self) -> float:
        """Return calibrated millimeters per source-image pixel."""
        pixel_length = hypot(
            self.second_pixel.x - self.first_pixel.x,
            self.second_pixel.y - self.first_pixel.y,
        )
        return self.known_length_mm / pixel_length

    def pixel_to_mm(self, point: PixelPoint) -> PointMM:
        """Transform image coordinates to model coordinates, with Y pointing upward."""
        scale = self.mm_per_pixel
        return PointMM(
            x=(point.x - self.origin_pixel.x) * scale,
            y=(self.origin_pixel.y - point.y) * scale,
        )
