"""Deterministic vector PDF rendering for floorplan projects."""

from __future__ import annotations

from math import cos, hypot, radians, sin
from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from electrical_floorplan_engine.models import FloorplanProject, PointMM


def _bounds(project: FloorplanProject) -> tuple[float, float, float, float]:
    points: list[PointMM] = []
    for wall in project.walls:
        points.extend((wall.start, wall.end))
    points.extend(symbol.position for symbol in project.symbols)
    for room in project.rooms:
        points.extend(room.vertices)
        if room.label_position is not None:
            points.append(room.label_position)

    if project.source_image and project.image_mm_per_pixel:
        image_width_px, image_height_px = ImageReader(project.source_image).getSize()
        scale = project.image_mm_per_pixel
        left = -project.image_origin_pixel_x * scale
        top = project.image_origin_pixel_y * scale
        points.extend(
            (
                PointMM(x=left, y=top),
                PointMM(x=left + image_width_px * scale, y=top - image_height_px * scale),
            )
        )

    if not points:
        return (0.0, 0.0, 100.0, 100.0)
    return (
        min(point.x for point in points),
        min(point.y for point in points),
        max(point.x for point in points),
        max(point.y for point in points),
    )


def _opening_endpoints(
    wall_start: PointMM, wall_end: PointMM, offset_mm: float, width_mm: float
) -> tuple[PointMM, PointMM]:
    dx = wall_end.x - wall_start.x
    dy = wall_end.y - wall_start.y
    length = hypot(dx, dy)
    ux, uy = dx / length, dy / length
    return (
        PointMM(
            x=wall_start.x + ux * offset_mm,
            y=wall_start.y + uy * offset_mm,
        ),
        PointMM(
            x=wall_start.x + ux * (offset_mm + width_mm),
            y=wall_start.y + uy * (offset_mm + width_mm),
        ),
    )


def render_pdf(project: FloorplanProject, output_path: str | Path) -> Path:
    """Render a project to a single-page landscape A4 PDF.

    The geometry and calibrated raster underlay are fitted to the printable page.
    The PDF is therefore a presentation output, not a guaranteed 1:1 scale drawing.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    page_width, page_height = landscape(A4)
    margin = project.margin_mm * mm
    title_height = 14 * mm
    available_width = page_width - 2 * margin
    available_height = page_height - 2 * margin - title_height

    min_x, min_y, max_x, max_y = _bounds(project)
    model_width = max(max_x - min_x, 1.0)
    model_height = max(max_y - min_y, 1.0)
    fit_scale = min(available_width / (model_width * mm), available_height / (model_height * mm))

    drawing_width = model_width * mm * fit_scale
    drawing_height = model_height * mm * fit_scale
    offset_x = margin + (available_width - drawing_width) / 2 - min_x * mm * fit_scale
    offset_y = margin + (available_height - drawing_height) / 2 - min_y * mm * fit_scale

    def xy(point: PointMM) -> tuple[float, float]:
        return (
            offset_x + point.x * mm * fit_scale,
            offset_y + point.y * mm * fit_scale,
        )

    pdf = canvas.Canvas(str(output), pagesize=landscape(A4), pageCompression=1)
    pdf.setTitle(project.title)
    pdf.setAuthor("Electrical Floorplan Engine")

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(margin, page_height - margin - 4 * mm, project.title)
    pdf.setFont("Helvetica", 7)
    pdf.drawRightString(
        page_width - margin,
        page_height - margin - 4 * mm,
        "SCHEMAT — dopasowany do arkusza; skala wydruku 1:1 nie jest gwarantowana",
    )

    # The raster is mapped from pixel coordinates into the calibrated model space.
    if project.source_image and project.image_mm_per_pixel:
        image_width_px, image_height_px = ImageReader(project.source_image).getSize()
        scale = project.image_mm_per_pixel
        image_left = -project.image_origin_pixel_x * scale
        image_bottom = (project.image_origin_pixel_y - image_height_px) * scale
        image_x, image_y = xy(PointMM(x=image_left, y=image_bottom))
        pdf.drawImage(
            ImageReader(project.source_image),
            image_x,
            image_y,
            width=image_width_px * scale * mm * fit_scale,
            height=image_height_px * scale * mm * fit_scale,
            preserveAspectRatio=False,
            mask="auto",
        )

    # Wall centerlines are schematic; optional thickness remains explicit model metadata.
    pdf.setStrokeColorRGB(0, 0, 0)
    pdf.setLineWidth(0.45 * mm)
    for wall in project.walls:
        x1, y1 = xy(wall.start)
        x2, y2 = xy(wall.end)
        pdf.line(x1, y1, x2, y2)

    # Openings are intervals along a host wall; all ranges are validated by the model.
    walls_by_id = {wall.id: wall for wall in project.walls}
    for opening in project.openings:
        wall = walls_by_id[opening.wall_id]
        first, second = _opening_endpoints(
            wall.start,
            wall.end,
            opening.offset_mm,
            opening.width_mm,
        )
        x1, y1 = xy(first)
        x2, y2 = xy(second)
        dx, dy = x2 - x1, y2 - y1
        page_length = hypot(dx, dy)
        ux, uy = dx / page_length, dy / page_length
        nx, ny = -uy, ux

        # Erase the schematic centerline through the opening.
        pdf.setStrokeColorRGB(1, 1, 1)
        pdf.setLineWidth(2.0 * mm)
        pdf.line(x1, y1, x2, y2)
        pdf.setStrokeColorRGB(0, 0, 0)
        pdf.setLineWidth(0.3 * mm)

        if opening.kind == "window":
            frame_offset = 1.1 * mm
            pdf.line(
                x1 + nx * frame_offset,
                y1 + ny * frame_offset,
                x2 + nx * frame_offset,
                y2 + ny * frame_offset,
            )
            pdf.line(
                x1 - nx * frame_offset,
                y1 - ny * frame_offset,
                x2 - nx * frame_offset,
                y2 - ny * frame_offset,
            )
        elif opening.kind == "door":
            hinge_x, hinge_y = (x1, y1) if opening.hinge_at == "start" else (x2, y2)
            side = 1.0 if opening.swing_side == "left" else -1.0
            pdf.line(
                hinge_x,
                hinge_y,
                hinge_x + nx * page_length * side,
                hinge_y + ny * page_length * side,
            )

        if opening.label:
            pdf.setFont("Helvetica", 6)
            pdf.drawCentredString((x1 + x2) / 2, (y1 + y2) / 2 + 1.8 * mm, opening.label[:32])

    # Room labels are placed at their area centroid or at an explicit model point.
    pdf.setFillColorRGB(0, 0, 0)
    for room in project.rooms:
        label_point = room.label_position or room.centroid
        label_x, label_y = xy(label_point)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawCentredString(label_x, label_y, room.name[:48])

    # Symbols are schematic until a formal symbol library is agreed.
    radius = max(1.6 * mm, min(2.5 * mm, fit_scale * 2.0 * mm))
    for symbol in project.symbols:
        x, y = xy(symbol.position)
        angle = radians(symbol.rotation_deg)
        pdf.setStrokeColorRGB(0, 0, 0)
        pdf.setFillColorRGB(0, 0, 0)
        pdf.setLineWidth(0.3 * mm)
        if symbol.kind == "light":
            pdf.circle(x, y, radius, stroke=1, fill=0)
            pdf.line(x - radius * 0.65, y - radius * 0.65, x + radius * 0.65, y + radius * 0.65)
            pdf.line(x - radius * 0.65, y + radius * 0.65, x + radius * 0.65, y - radius * 0.65)
        elif symbol.kind == "switch":
            pdf.circle(x, y, radius, stroke=1, fill=0)
            pdf.line(x, y, x + cos(angle) * radius * 1.8, y + sin(angle) * radius * 1.8)
        elif symbol.kind == "socket":
            pdf.circle(x, y, radius, stroke=1, fill=0)
            pdf.circle(x, y, radius * 0.18, stroke=1, fill=0)
        elif symbol.kind == "junction":
            pdf.circle(x, y, radius * 0.7, stroke=1, fill=1)
        else:
            pdf.rect(x - radius, y - radius, 2 * radius, 2 * radius, stroke=1, fill=0)
        if symbol.label:
            pdf.setFont("Helvetica", 7)
            pdf.drawString(x + radius + 1.2 * mm, y + radius, symbol.label[:48])

    footer_y = margin * 0.55
    pdf.setFont("Helvetica", 7)
    pdf.drawString(
        margin,
        footer_y,
        (
            f"Jednostki modelu: mm | Ściany: {len(project.walls)} "
            f"| Otwory: {len(project.openings)} | Pomieszczenia: {len(project.rooms)} "
            f"| Symbole: {len(project.symbols)}"
        ),
    )
    if project.notes:
        pdf.drawRightString(page_width - margin, footer_y, project.notes[0][:100])

    pdf.showPage()
    pdf.save()
    return output
