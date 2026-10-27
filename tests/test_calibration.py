import pytest
from pydantic import ValidationError

from electrical_floorplan_engine.calibration import PixelPoint, ScaleCalibration


def test_calibration_computes_mm_per_pixel_and_transforms_point() -> None:
    calibration = ScaleCalibration(
        first_pixel=PixelPoint(x=10, y=20),
        second_pixel=PixelPoint(x=110, y=20),
        known_length_mm=2000,
        origin_pixel=PixelPoint(x=10, y=20),
    )

    assert calibration.mm_per_pixel == pytest.approx(20.0)
    assert calibration.pixel_to_mm(PixelPoint(x=60, y=70)).x == pytest.approx(1000.0)
    assert calibration.pixel_to_mm(PixelPoint(x=60, y=70)).y == pytest.approx(-1000.0)


def test_calibration_rejects_zero_length_reference() -> None:
    with pytest.raises(ValidationError):
        ScaleCalibration(
            first_pixel=PixelPoint(x=4, y=5),
            second_pixel=PixelPoint(x=4, y=5),
            known_length_mm=1000,
        )


def test_calibration_rejects_non_positive_known_length() -> None:
    with pytest.raises(ValidationError):
        ScaleCalibration(
            first_pixel=PixelPoint(x=0, y=0),
            second_pixel=PixelPoint(x=10, y=0),
            known_length_mm=0,
        )
