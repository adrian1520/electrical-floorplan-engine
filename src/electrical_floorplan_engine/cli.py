"""Command-line interface for the floorplan engine."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from pydantic import ValidationError

from electrical_floorplan_engine.models import FloorplanProject
from electrical_floorplan_engine.rendering.pdf import render_pdf

logger = logging.getLogger(__name__)


def main() -> int:
    """Validate a project JSON file and export it to PDF."""
    parser = argparse.ArgumentParser(description="Validate a floorplan project and render PDF.")
    parser.add_argument("project", type=Path, help="Path to project JSON")
    parser.add_argument("-o", "--output", type=Path, default=Path("floorplan.pdf"))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)
    try:
        raw = json.loads(args.project.read_text(encoding="utf-8"))
        project = FloorplanProject.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        logger.error("Cannot load a valid project: %s", exc)
        return 2

    output = render_pdf(project, args.output)
    logger.info("PDF written to %s", output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
