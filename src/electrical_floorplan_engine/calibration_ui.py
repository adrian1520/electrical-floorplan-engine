"""Generate a self-contained, offline browser UI for visual raster calibration."""

from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path


_HTML_TEMPLATE = r"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light">
<title>Kalibracja rzutu — Electrical Floorplan Engine</title>
<style>
:root { color-scheme: light; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #17212b; background: #f3f5f7; }
* { box-sizing: border-box; }
body { margin: 0; }
header { background: #13283c; color: white; padding: 18px max(16px, env(safe-area-inset-left)); }
header h1 { margin: 0 0 6px; font-size: 1.25rem; }
header p { margin: 0; color: #cbd8e4; font-size: .92rem; }
main { display: grid; grid-template-columns: minmax(280px, 340px) minmax(0, 1fr); gap: 16px; padding: 16px; align-items: start; }
.panel { background: white; border: 1px solid #d9e0e6; border-radius: 12px; padding: 16px; }
.panel h2 { font-size: 1rem; margin: 0 0 10px; }
.field { display: grid; gap: 6px; margin: 12px 0; }
label { font-size: .9rem; font-weight: 650; }
input[type=number] { font: inherit; min-height: 44px; width: 100%; border: 1px solid #9ba9b6; border-radius: 8px; padding: 8px 10px; }
.button-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }
button { font: inherit; cursor: pointer; border: 1px solid #a9b6c2; background: white; color: #182a3b; border-radius: 8px; min-height: 44px; padding: 9px 12px; }
button:focus-visible, input:focus-visible { outline: 3px solid #78b8ef; outline-offset: 2px; }
button[aria-pressed=true] { color: white; background: #125b91; border-color: #125b91; }
button.primary { background: #12663b; border-color: #12663b; color: white; width: 100%; font-weight: 700; }
button.primary:disabled { opacity: .45; cursor: not-allowed; }
.muted { color: #52616e; font-size: .88rem; line-height: 1.45; }
.status { min-height: 3rem; background: #f0f4f7; border-radius: 8px; padding: 10px; font-size: .9rem; line-height: 1.45; overflow-wrap: anywhere; }
.status.error { color: #912d25; background: #fff0ee; }
#scale-result { font-weight: 700; font-variant-numeric: tabular-nums; }
.viewer-panel { min-width: 0; }
.viewer-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
#viewer { overflow: auto; max-height: 75vh; min-height: 300px; border: 1px solid #bec9d2; border-radius: 8px; background: #e1e6eb; overscroll-behavior: contain; }
#stage { position: relative; margin: 0; }
#plan-image { position: absolute; inset: 0; width: 100%; height: 100%; user-select: none; -webkit-user-drag: none; }
#overlay { position: absolute; inset: 0; width: 100%; height: 100%; cursor: crosshair; touch-action: manipulation; }
.point-label { font: 700 16px system-ui, sans-serif; fill: white; text-anchor: middle; dominant-baseline: central; pointer-events: none; }
.legend { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 10px; font-size: .82rem; color: #465562; }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; }
@media (max-width: 820px) {
  main { grid-template-columns: 1fr; padding: 10px; gap: 10px; }
  header { padding: 14px 16px; }
  #viewer { max-height: 62vh; min-height: 260px; }
  .panel { padding: 13px; }
}
</style>
</head>
<body>
<header>
  <h1>Kalibracja rzutu</h1>
  <p id="project-title">Electrical Floorplan Engine · praca lokalna</p>
</header>
<main>
  <section class="panel" aria-labelledby="instructions-title">
    <h2 id="instructions-title">1. Wybierz wymiar odniesienia</h2>
    <p class="muted">Zaznacz na planie dwa końce znanego wymiaru. W miarę możliwości wybierz długi, czytelny odcinek. Współrzędne są mierzone w pikselach oryginalnego obrazu, nawet gdy widok jest powiększony.</p>
    <div class="field">
      <label for="known-length">Znana długość (mm)</label>
      <input id="known-length" type="number" min="0.001" step="any" inputmode="decimal" placeholder="np. 3000">
    </div>
    <h2>2. Zaznacz punkty na obrazie</h2>
    <div class="button-row" role="group" aria-label="Wybierz punkt do zaznaczenia">
      <button type="button" data-mode="first" aria-pressed="true">A · początek</button>
      <button type="button" data-mode="second" aria-pressed="false">B · koniec</button>
      <button type="button" data-mode="origin" aria-pressed="false">O · początek układu</button>
    </div>
    <div id="point-status" class="status" aria-live="polite">Kliknij lub dotknij punkt A na obrazie.</div>
    <p class="muted">Punkt O definiuje (0, 0) modelu. Domyślnie użyjemy A. Aby ustawić inne miejsce układu, wybierz „O · początek układu” i dotknij planu.</p>
    <h2>3. Wynik</h2>
    <div class="status">
      <div>Odległość na obrazie: <span id="pixel-distance">—</span> px</div>
      <div>Skala: <span id="scale-result">—</span></div>
      <div class="muted" id="origin-result">Punkt O: taki sam jak A</div>
    </div>
    <div class="button-row">
      <button type="button" id="clear-points">Wyczyść punkty</button>
    </div>
    <button type="button" id="export-json" class="primary" disabled>Pobierz skalibrowany JSON</button>
    <p class="muted">Plik JSON zapisz obok oryginalnego pliku projektu i obrazu, aby względna ścieżka <code>source_image</code> nadal działała. Zweryfikuj wynik na drugim znanym wymiarze.</p>
    <div id="message" class="status" role="status" aria-live="polite">Obraz jest osadzony w tym pliku HTML. Panel nie wysyła danych do sieci.</div>
  </section>
  <section class="panel viewer-panel" aria-labelledby="image-title">
    <h2 id="image-title">Plan źródłowy</h2>
    <div class="viewer-toolbar">
      <span class="muted" id="image-info">Wczytywanie obrazu…</span>
      <div class="button-row" style="margin:0">
        <button type="button" id="zoom-out" aria-label="Pomniejsz obraz">−</button>
        <button type="button" id="fit-view">Dopasuj</button>
        <button type="button" id="zoom-in" aria-label="Powiększ obraz">+</button>
      </div>
    </div>
    <div id="viewer" aria-label="Obraz rzutu; dotknij wybranego miejsca">
      <div id="stage">
        <img id="plan-image" alt="Rzut źródłowy">
        <svg id="overlay" role="img" aria-label="Wybór punktów kalibracyjnych"></svg>
      </div>
    </div>
    <div class="legend">
      <span><i class="dot" style="background:#0877c9"></i>A — pierwszy punkt</span>
      <span><i class="dot" style="background:#d65a19"></i>B — drugi punkt</span>
      <span><i class="dot" style="background:#138044"></i>O — początek układu</span>
    </div>
  </section>
</main>
<script>
"use strict";
const EMBEDDED_IMAGE = "__IMAGE_DATA_URI__";
const PROJECT_BASE64 = "__PROJECT_BASE64__";
const SOURCE_NAME_BASE64 = "__SOURCE_NAME_BASE64__";

function decodeUtf8Base64(text) {
  const binary = atob(text);
  const bytes = Uint8Array.from(binary, character => character.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}
const initialProject = JSON.parse(decodeUtf8Base64(PROJECT_BASE64));
const sourceName = decodeUtf8Base64(SOURCE_NAME_BASE64);
const image = document.getElementById("plan-image");
const overlay = document.getElementById("overlay");
const stage = document.getElementById("stage");
const viewer = document.getElementById("viewer");
const lengthInput = document.getElementById("known-length");
const exportButton = document.getElementById("export-json");
const pointStatus = document.getElementById("point-status");
const message = document.getElementById("message");
const pixelDistance = document.getElementById("pixel-distance");
const scaleResult = document.getElementById("scale-result");
const originResult = document.getElementById("origin-result");
const imageInfo = document.getElementById("image-info");
let mode = "first";
let points = { first: null, second: null, origin: null };
let zoom = 1;
let naturalWidth = 0;
let naturalHeight = 0;

document.getElementById("project-title").textContent =
  (initialProject.title || "Projekt") + " · kalibracja lokalna";
image.alt = "Rzut: " + sourceName;
image.src = EMBEDDED_IMAGE;

function fitZoom() {
  if (!naturalWidth) return;
  const availableWidth = Math.max(200, viewer.clientWidth - 24);
  zoom = Math.min(1, availableWidth / naturalWidth);
  applyZoom();
}
function applyZoom() {
  if (!naturalWidth) return;
  const width = Math.max(1, Math.round(naturalWidth * zoom));
  const height = Math.max(1, Math.round(naturalHeight * zoom));
  stage.style.width = width + "px";
  stage.style.height = height + "px";
  overlay.setAttribute("viewBox", "0 0 " + naturalWidth + " " + naturalHeight);
  renderPoints();
}
function selectMode(nextMode) {
  mode = nextMode;
  document.querySelectorAll("[data-mode]").forEach(button => {
    button.setAttribute("aria-pressed", String(button.dataset.mode === mode));
  });
  const labels = { first: "A", second: "B", origin: "O" };
  pointStatus.textContent = "Dotknij obrazu, aby ustawić punkt " + labels[mode] + ".";
}
document.querySelectorAll("[data-mode]").forEach(button => {
  button.addEventListener("click", () => selectMode(button.dataset.mode));
});

function svgElement(name, attrs, text) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(attrs || {}).forEach(([key, value]) => element.setAttribute(key, String(value)));
  if (text !== undefined) element.textContent = text;
  return element;
}
function renderPoints() {
  while (overlay.firstChild) overlay.removeChild(overlay.firstChild);
  const colors = { first: "#0877c9", second: "#d65a19", origin: "#138044" };
  const labels = { first: "A", second: "B", origin: "O" };
  if (points.first && points.second) {
    overlay.appendChild(svgElement("line", {
      x1: points.first.x, y1: points.first.y, x2: points.second.x, y2: points.second.y,
      stroke: "#f6bd16", "stroke-width": 3 / zoom, "stroke-dasharray": (7 / zoom) + " " + (5 / zoom)
    }));
  }
  ["first", "second", "origin"].forEach(key => {
    const point = key === "origin" ? points.origin : points[key];
    if (!point) return;
    const radius = 10 / zoom;
    overlay.appendChild(svgElement("circle", {
      cx: point.x, cy: point.y, r: radius,
      fill: colors[key], stroke: "white", "stroke-width": 3 / zoom
    }));
    overlay.appendChild(svgElement("text", {
      x: point.x, y: point.y, class: "point-label", "font-size": 16 / zoom
    }, labels[key]));
  });
  updateResult();
}
function updateResult() {
  const length = Number(lengthInput.value);
  const validLength = Number.isFinite(length) && length > 0;
  const distance = points.first && points.second
    ? Math.hypot(points.second.x - points.first.x, points.second.y - points.first.y) : 0;
  const validPoints = distance > 0;
  pixelDistance.textContent = validPoints ? distance.toFixed(2) : "—";
  scaleResult.textContent = validPoints && validLength
    ? (length / distance).toPrecision(7) + " mm/px" : "—";
  const origin = points.origin || points.first;
  originResult.textContent = origin
    ? "Punkt O: (" + origin.x.toFixed(2) + ", " + origin.y.toFixed(2) + ") px"
    : "Punkt O: taki sam jak A";
  exportButton.disabled = !(validPoints && validLength);
}
overlay.addEventListener("click", event => {
  if (!naturalWidth) return;
  const rect = overlay.getBoundingClientRect();
  const point = {
    x: Math.min(naturalWidth, Math.max(0, (event.clientX - rect.left) * naturalWidth / rect.width)),
    y: Math.min(naturalHeight, Math.max(0, (event.clientY - rect.top) * naturalHeight / rect.height))
  };
  points[mode] = point;
  const labels = { first: "A", second: "B", origin: "O" };
  pointStatus.textContent = "Punkt " + labels[mode] + ": X=" + point.x.toFixed(2)
    + " px, Y=" + point.y.toFixed(2) + " px.";
  message.textContent = "Punkty są przechowywane lokalnie w przeglądarce.";
  message.classList.remove("error");
  renderPoints();
  if (mode === "first") selectMode("second");
  else if (mode === "second" && !points.origin) selectMode("origin");
});
lengthInput.addEventListener("input", updateResult);
document.getElementById("zoom-in").addEventListener("click", () => {
  zoom = Math.min(8, zoom * 1.25);
  applyZoom();
});
document.getElementById("zoom-out").addEventListener("click", () => {
  zoom = Math.max(0.03, zoom / 1.25);
  applyZoom();
});
document.getElementById("fit-view").addEventListener("click", fitZoom);
document.getElementById("clear-points").addEventListener("click", () => {
  points = { first: null, second: null, origin: null };
  selectMode("first");
  message.textContent = "Punkty wyczyszczone.";
  renderPoints();
});
image.addEventListener("load", () => {
  naturalWidth = image.naturalWidth;
  naturalHeight = image.naturalHeight;
  if (!naturalWidth || !naturalHeight) {
    message.textContent = "Nie udało się odczytać wymiarów obrazu.";
    message.classList.add("error");
    return;
  }
  imageInfo.textContent = sourceName + " · " + naturalWidth + " × " + naturalHeight + " px";
  fitZoom();
});
image.addEventListener("error", () => {
  imageInfo.textContent = "Nie można wyświetlić obrazu";
  message.textContent = "Format obrazu może nie być obsługiwany przez tę przeglądarkę. Użyj PNG, JPEG lub WebP.";
  message.classList.add("error");
});
window.addEventListener("resize", () => {
  if (naturalWidth && zoom < 1) fitZoom();
});

exportButton.addEventListener("click", () => {
  const length = Number(lengthInput.value);
  const distance = Math.hypot(points.second.x - points.first.x, points.second.y - points.first.y);
  if (!(length > 0 && distance > 0)) return;
  const origin = points.origin || points.first;
  const calibratedProject = Object.assign({}, initialProject, {
    image_mm_per_pixel: length / distance,
    image_origin_pixel_x: origin.x,
    image_origin_pixel_y: origin.y
  });
  const output = JSON.stringify(calibratedProject, null, 2) + "\n";
  const blob = new Blob([output], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  const safeTitle = String(initialProject.title || "plan")
    .normalize("NFKD").replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-+|-+$/g, "") || "plan";
  anchor.download = safeTitle + ".calibrated.json";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
  message.textContent = "Przygotowano skalibrowany JSON. Zapisz go obok oryginalnego pliku projektu i obrazu.";
  message.classList.remove("error");
});
</script>
</body>
</html>
"""


def _base64_text(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def create_calibration_ui(
    project_path: str | Path, output_path: str | Path | None = None
) -> Path:
    """Build a self-contained HTML calibration tool from a project JSON and its raster."""
    project_file = Path(project_path).resolve()
    raw = json.loads(project_file.read_text(encoding="utf-8"))
    source_image = raw.get("source_image")
    if not source_image:
        raise ValueError("Project JSON must define source_image to create the calibration UI.")

    image_path = Path(source_image)
    if not image_path.is_absolute():
        image_path = (project_file.parent / image_path).resolve()
    if not image_path.is_file():
        raise FileNotFoundError(f"Source image does not exist: {image_path}")

    mime_type, _ = mimetypes.guess_type(image_path.name)
    if not mime_type or not mime_type.startswith("image/"):
        raise ValueError(f"Cannot determine image MIME type for {image_path.name!r}")

    image_payload = base64.b64encode(image_path.read_bytes()).decode("ascii")
    image_data_uri = f"data:{mime_type};base64,{image_payload}"
    project_payload = _base64_text(json.dumps(raw, ensure_ascii=False))
    filename_payload = _base64_text(image_path.name)
    html = (
        _HTML_TEMPLATE.replace("__IMAGE_DATA_URI__", image_data_uri)
        .replace("__PROJECT_BASE64__", project_payload)
        .replace("__SOURCE_NAME_BASE64__", filename_payload)
    )

    output = Path(output_path) if output_path is not None else project_file.with_name(
        f"{project_file.stem}.calibration.html"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return output
