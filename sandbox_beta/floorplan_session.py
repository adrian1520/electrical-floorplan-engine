"""Offline session helpers for the Electrical Floorplan Engine ChatGPT beta.

Runs against a checkout of this repository. No server, network calls, external
uploads, or credentials. PDF rendering requires PyMuPDF (fitz) already installed.
"""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import Any, Sequence

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def calibration_scale(first_pixel: Sequence[float], second_pixel: Sequence[float], known_length_mm: float) -> float:
    """Calculate mm/pixel from two image points and a positive known length."""
    if len(first_pixel) != 2 or len(second_pixel) != 2:
        raise ValueError("Punkty muszą być parami (x, y).")
    x1, y1 = map(float, first_pixel)
    x2, y2 = map(float, second_pixel)
    length = float(known_length_mm)
    if not all(math.isfinite(v) for v in (x1, y1, x2, y2, length)):
        raise ValueError("Współrzędne i długość muszą być liczbami skończonymi.")
    pixels = math.hypot(x2 - x1, y2 - y1)
    if pixels <= 0 or length <= 0:
        raise ValueError("Punkty muszą być różne, a długość dodatnia.")
    return length / pixels


def pixel_to_mm(pixel: Sequence[float], origin_pixel: Sequence[float], mm_per_pixel: float) -> dict[str, float]:
    """Transform image coordinates (Y down) to model mm (Y up)."""
    if len(pixel) != 2 or len(origin_pixel) != 2:
        raise ValueError("Punkty muszą być parami (x, y).")
    x, y = map(float, pixel)
    ox, oy = map(float, origin_pixel)
    scale = float(mm_per_pixel)
    if not all(math.isfinite(v) for v in (x, y, ox, oy, scale)) or scale <= 0:
        raise ValueError("Nieprawidłowe współrzędne lub skala.")
    return {"x": (x - ox) * scale, "y": (oy - y) * scale}


def apply_calibration(project: dict[str, Any], first_pixel: Sequence[float],
                      second_pixel: Sequence[float], known_length_mm: float, *,
                      origin_pixel: Sequence[float] | None = None) -> dict[str, Any]:
    """Set scale/origin metadata in an uncalibrated draft and return a copy."""
    result = json.loads(json.dumps(project))
    if not result.get("source_image"):
        raise ValueError("Projekt musi wskazywać raster źródłowy.")
    origin = origin_pixel if origin_pixel is not None else first_pixel
    if len(origin) != 2:
        raise ValueError("Początek układu musi być parą (x, y).")
    result["image_mm_per_pixel"] = calibration_scale(first_pixel, second_pixel, known_length_mm)
    result["image_origin_pixel_x"] = float(origin[0])
    result["image_origin_pixel_y"] = float(origin[1])
    return result


def add_wall_from_pixels(project: dict[str, Any], object_id: str,
                         start_pixel: Sequence[float], end_pixel: Sequence[float], *,
                         thickness_mm: float | None = None, role: str = "unknown") -> dict[str, Any]:
    """Add a wall after calibration; returns the newly added model-space object."""
    scale = project.get("image_mm_per_pixel")
    if scale is None:
        raise ValueError("Skalibruj projekt przed tworzeniem geometrii wymiarowanej.")
    if role not in {"exterior", "interior", "partition", "unknown"}:
        raise ValueError("Nieznana rola ściany.")
    existing = {item.get("id") for key in ("walls", "openings", "rooms", "symbols")
                for item in project.get(key, [])}
    if not object_id or object_id in existing:
        raise ValueError("ID obiektu musi być niepuste i unikalne.")
    origin = (project.get("image_origin_pixel_x", 0), project.get("image_origin_pixel_y", 0))
    wall = {"id": object_id, "start": pixel_to_mm(start_pixel, origin, scale),
            "end": pixel_to_mm(end_pixel, origin, scale), "role": role}
    if wall["start"] == wall["end"]:
        raise ValueError("Ściana nie może mieć zerowej długości.")
    if thickness_mm is not None:
        thickness = float(thickness_mm)
        if not math.isfinite(thickness) or thickness <= 0:
            raise ValueError("Grubość ściany musi być dodatnia.")
        wall["thickness_mm"] = thickness
    project.setdefault("walls", []).append(wall)
    return wall


def add_room_from_pixels(project: dict[str, Any], object_id: str, name: str,
                         vertices_pixel: Sequence[Sequence[float]]) -> dict[str, Any]:
    """Add a polygon; the repository model remains the final full validator."""
    scale = project.get("image_mm_per_pixel")
    if scale is None:
        raise ValueError("Skalibruj projekt przed tworzeniem geometrii wymiarowanej.")
    if len(vertices_pixel) < 3 or not name or len(name) > 80:
        raise ValueError("Pomieszczenie wymaga nazwy i co najmniej trzech wierzchołków.")
    existing = {item.get("id") for key in ("walls", "openings", "rooms", "symbols")
                for item in project.get(key, [])}
    if not object_id or object_id in existing:
        raise ValueError("ID obiektu musi być niepuste i unikalne.")
    origin = (project.get("image_origin_pixel_x", 0), project.get("image_origin_pixel_y", 0))
    vertices = [pixel_to_mm(point, origin, scale) for point in vertices_pixel]
    if len({(p["x"], p["y"]) for p in vertices}) != len(vertices):
        raise ValueError("Obrys nie może powtarzać wierzchołków.")
    area2 = sum(vertices[i]["x"] * vertices[(i + 1) % len(vertices)]["y"]
                - vertices[(i + 1) % len(vertices)]["x"] * vertices[i]["y"]
                for i in range(len(vertices)))
    if abs(area2) < 1e-7:
        raise ValueError("Obrys ma zerową powierzchnię.")
    room = {"id": object_id, "name": name, "vertices": vertices}
    project.setdefault("rooms", []).append(room)
    return room


def initialize_session(source_file: str | Path, workspace: str | Path, *,
                       title: str | None = None, pdf_page: int = 1, dpi: int = 200) -> dict[str, str]:
    """Copy an image or rasterize one PDF page and create a deliberately uncalibrated project."""
    source = Path(source_file).expanduser().resolve()
    directory = Path(workspace).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Nie znaleziono pliku źródłowego: {source}")
    directory.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".pdf":
        if page_number_invalid := (pdf_page < 1 or not 72 <= dpi <= 600):
            raise ValueError("Numer strony lub DPI jest poza zakresem.")
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError("Brak lokalnie dostępnego PyMuPDF. Prześlij stronę PDF jako PNG/JPG zamiast instalować pakiety z sieci.") from exc
        with fitz.open(source) as pdf:
            if pdf_page > pdf.page_count:
                raise ValueError(f"PDF ma {pdf.page_count} stron; wskazano stronę {pdf_page}.")
            pixmap = pdf.load_page(pdf_page - 1).get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
            raster = directory / f"{source.stem}_page_{pdf_page:03d}.png"
            pixmap.save(raster)
        note = f"Źródło: {source.name}; strona PDF: {pdf_page}; {dpi} DPI."
    else:
        if source.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError(f"Nieobsługiwany format obrazu: {source.suffix}")
        raster = directory / source.name
        if source != raster.resolve():
            if raster.exists():
                raster = directory / f"{source.stem}_source{source.suffix.lower()}"
            shutil.copy2(source, raster)
        note = f"Źródło: {source.name}; obraz użyty jako podkład."
    project = {
        "title": title.strip() if title and title.strip() else source.stem.replace("_", " ").replace("-", " "),
        "units": "mm", "walls": [], "openings": [], "rooms": [], "symbols": [],
        "margin_mm": 15, "source_image": raster.name,
        "image_origin_pixel_x": 0, "image_origin_pixel_y": 0,
        "notes": ["Beta sandbox: geometria nie została automatycznie rozpoznana.", note]
    }
    project_path = directory / "project.json"
    project_path.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"workspace": str(directory), "project_json": str(project_path), "source_raster": str(raster)}


def make_calibration_editor(project_json: str | Path, output_html: str | Path | None = None) -> str:
    """Generate the repository's self-contained local calibration HTML."""
    from electrical_floorplan_engine.calibration_ui import create_calibration_ui
    return str(create_calibration_ui(Path(project_json), Path(output_html) if output_html else None))


def make_geometry_editor(calibrated_project_json: str | Path, output_html: str | Path | None = None) -> str:
    """Generate the repository's self-contained local geometry editor HTML."""
    from electrical_floorplan_engine.geometry_ui import create_geometry_ui
    return str(create_geometry_ui(Path(calibrated_project_json), Path(output_html) if output_html else None))


def validate_and_export(project_json: str | Path, output_pdf: str | Path | None = None, *,
                        output_report_json: str | Path | None = None) -> dict[str, Any]:
    """Validate a calibrated project, list geometry warnings and optionally render PDF."""
    from electrical_floorplan_engine.geometry import validate_geometry
    from electrical_floorplan_engine.models import FloorplanProject
    from electrical_floorplan_engine.rendering.pdf import render_pdf

    source = Path(project_json).expanduser().resolve()
    raw = json.loads(source.read_text(encoding="utf-8"))
    if raw.get("source_image"):
        image_path = Path(raw["source_image"])
        if not image_path.is_absolute():
            raw["source_image"] = str((source.parent / image_path).resolve())
    project = FloorplanProject.model_validate(raw)
    report: dict[str, Any] = {
        "valid": True, "title": project.title, "units": project.units,
        "calibrated": project.image_mm_per_pixel is not None,
        "objects": {"walls": len(project.walls), "openings": len(project.openings),
                    "rooms": len(project.rooms), "symbols": len(project.symbols)},
        "warnings": [issue.to_dict() for issue in validate_geometry(project)],
        "pdf": str(render_pdf(project, Path(output_pdf).expanduser().resolve())) if output_pdf else None,
        "project_json": str(source),
    }
    if output_report_json:
        report_path = Path(output_report_json).expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["report_json"] = str(report_path)
    return report


def restore_relative_image_path(project_json: str | Path) -> str:
    """Return an existing source image path as absolute for inspection."""
    source = Path(project_json).expanduser().resolve()
    raw = json.loads(source.read_text(encoding="utf-8"))
    image = raw.get("source_image")
    if not image:
        raise ValueError("Projekt nie ma wskazanego obrazu źródłowego.")
    path = Path(image)
    if not path.is_absolute():
        path = source.parent / path
    if not path.is_file():
        raise FileNotFoundError(f"Nie znaleziono rastra źródłowego: {path}")
    return str(path.resolve())
