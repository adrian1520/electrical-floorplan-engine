"""Command-line interface for the floorplan engine."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from electrical_floorplan_engine.calibration import PixelPoint, ScaleCalibration
from electrical_floorplan_engine.geometry import validate_geometry
from electrical_floorplan_engine.models import FloorplanProject
from electrical_floorplan_engine.rendering.pdf import render_pdf

logger = logging.getLogger(__name__)


def _parse_pixel(value: str) -> PixelPoint:
    """Parse a pixel coordinate in the form X,Y."""
    try:
        x_text, y_text = value.split(",", maxsplit=1)
        return PixelPoint(x=float(x_text), y=float(y_text))
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError("Pixel coordinates must use the form X,Y.") from exc


def _calibrate(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="floorplan-engine calibrate",
        description="Calculate raster scale and write a calibrated project JSON.",
    )
    parser.add_argument("--project", type=Path, required=True, help="Input project JSON")
    parser.add_argument("--first-pixel", type=_parse_pixel, required=True, metavar="X,Y")
    parser.add_argument("--second-pixel", type=_parse_pixel, required=True, metavar="X,Y")
    parser.add_argument("--length-mm", type=float, required=True, help="Known distance in mm")
    parser.add_argument(
        "--origin-pixel",
        type=_parse_pixel,
        help="Pixel representing model origin; defaults to --first-pixel",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON (default: input filename with .calibrated.json suffix)",
    )
    args = parser.parse_args(argv)

    try:
        input_path = args.project.resolve()
        raw = json.loads(input_path.read_text(encoding="utf-8"))
        if not raw.get("source_image"):
            raise ValueError("Input project JSON must define source_image before calibration.")
        origin = args.origin_pixel or args.first_pixel
        calibration = ScaleCalibration(
            first_pixel=args.first_pixel,
            second_pixel=args.second_pixel,
            known_length_mm=args.length_mm,
            origin_pixel=origin,
        )
        raw["image_mm_per_pixel"] = calibration.mm_per_pixel
        raw["image_origin_pixel_x"] = origin.x
        raw["image_origin_pixel_y"] = origin.y
        output = args.output or input_path.with_name(f"{input_path.stem}.calibrated.json")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        logger.error("Cannot calibrate project: %s", exc)
        return 2

    print(f"Scale: {calibration.mm_per_pixel:.9g} mm/pixel")
    print(output)
    return 0


def _check(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="floorplan-engine check",
        description="Validate project data and report likely geometry issues.",
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("--tolerance-mm", type=float, default=1.0)
    parser.add_argument("--strict", action="store_true", help="Return 1 if any warning is found")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args(argv)

    try:
        raw = json.loads(args.project.read_text(encoding="utf-8"))
        project = FloorplanProject.model_validate(raw)
        issues = validate_geometry(project, tolerance_mm=args.tolerance_mm)
    except (OSError, json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        logger.error("Cannot validate project: %s", exc)
        return 2

    if args.json:
        print(
            json.dumps(
                {"valid": True, "issues": [issue.to_dict() for issue in issues]},
                ensure_ascii=False,
                indent=2,
            )
        )
    elif not issues:
        print("No geometry warnings.")
    else:
        for issue in issues:
            object_names = ", ".join(issue.object_ids)
            print(f"[{issue.severity}] {issue.code} ({object_names}): {issue.message}")

    return 1 if args.strict and issues else 0


def _render(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate a project JSON file and render PDF.")
    parser.add_argument("project", type=Path, help="Path to project JSON")
    parser.add_argument("-o", "--output", type=Path, default=Path("floorplan.pdf"))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)
    try:
        raw = json.loads(args.project.read_text(encoding="utf-8"))
        if raw.get("source_image"):
            image_path = Path(raw["source_image"])
            if not image_path.is_absolute():
                raw["source_image"] = str((args.project.resolve().parent / image_path).resolve())
        project = FloorplanProject.model_validate(raw)
        for issue in validate_geometry(project):
            logger.warning("%s: %s", issue.code, issue.message)
        output = render_pdf(project, args.output)
    except (OSError, json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        logger.error("Cannot load project or render PDF: %s", exc)
        return 2

    logger.info("PDF written to %s", output)
    print(output)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch calibration, validation, or the backward-compatible PDF renderer."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    logging.basicConfig(level=logging.WARNING)
    if arguments and arguments[0] == "calibrate":
        return _calibrate(arguments[1:])
    if arguments and arguments[0] == "check":
        return _check(arguments[1:])
    return _render(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
