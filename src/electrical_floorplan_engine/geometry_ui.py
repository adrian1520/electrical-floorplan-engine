"""Generate an offline visual editor for calibrated floorplan geometry."""

from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path

from electrical_floorplan_engine.models import FloorplanProject


_HTML_TEMPLATE = r"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light">
<title>Edytor geometrii — Electrical Floorplan Engine</title>
<style>
:root { color-scheme: light; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #17212b; background: #f3f5f7; }
* { box-sizing: border-box; }
body { margin: 0; }
header { background: #13283c; color: white; padding: 16px max(16px, env(safe-area-inset-left)); }
header h1 { margin: 0 0 5px; font-size: 1.2rem; }
header p { margin: 0; color: #cbd8e4; font-size: .9rem; }
main { display: grid; grid-template-columns: minmax(290px, 360px) minmax(0, 1fr); gap: 14px; padding: 14px; align-items: start; }
.panel { background: white; border: 1px solid #d9e0e6; border-radius: 12px; padding: 14px; min-width: 0; }
h2 { font-size: 1rem; margin: 0 0 9px; }
h3 { font-size: .92rem; margin: 16px 0 7px; }
.field { display: grid; gap: 5px; margin: 9px 0; }
label { font-size: .86rem; font-weight: 650; }
input, select { min-height: 40px; width: 100%; font: inherit; border: 1px solid #9ba9b6; border-radius: 7px; padding: 7px 9px; background: white; color: #182a3b; }
input[type=checkbox] { width: 18px; min-height: 18px; }
.checkbox-row { display: flex; gap: 8px; align-items: center; margin: 10px 0; }
.button-row { display: flex; flex-wrap: wrap; gap: 7px; margin: 9px 0; }
button { font: inherit; cursor: pointer; border: 1px solid #a9b6c2; background: white; color: #182a3b; border-radius: 7px; min-height: 40px; padding: 8px 10px; }
button:focus-visible, input:focus-visible, select:focus-visible { outline: 3px solid #78b8ef; outline-offset: 2px; }
button[aria-pressed=true] { color: white; background: #125b91; border-color: #125b91; }
button.primary { background: #12663b; border-color: #12663b; color: white; width: 100%; font-weight: 700; }
button.danger { color: #9a2e27; border-color: #d7a6a2; }
button:disabled { opacity: .45; cursor: not-allowed; }
.muted { color: #52616e; font-size: .84rem; line-height: 1.4; }
.status { min-height: 2.7rem; background: #f0f4f7; border-radius: 7px; padding: 9px; font-size: .88rem; line-height: 1.4; overflow-wrap: anywhere; }
.status.error { color: #912d25; background: #fff0ee; }
.status.success { color: #145b35; background: #eaf6ef; }
#viewer { overflow: auto; max-height: 78vh; min-height: 300px; border: 1px solid #bec9d2; border-radius: 8px; background: #e1e6eb; overscroll-behavior: contain; }
#stage { position: relative; margin: 0; }
#plan-image { position: absolute; inset: 0; width: 100%; height: 100%; user-select: none; -webkit-user-drag: none; }
#overlay { position: absolute; inset: 0; width: 100%; height: 100%; cursor: crosshair; touch-action: none; }
.toolbar { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 9px; }
.legend { display: flex; flex-wrap: wrap; gap: 11px; margin-top: 9px; font-size: .8rem; color: #465562; }
.legend span { display: inline-flex; align-items: center; gap: 5px; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; }
#object-list { margin: 6px 0 0; padding-left: 18px; font-size: .83rem; color: #465562; max-height: 130px; overflow: auto; }
code { overflow-wrap: anywhere; }
@media (max-width: 900px) {
  main { grid-template-columns: 1fr; padding: 9px; gap: 9px; }
  #viewer { max-height: 63vh; min-height: 260px; }
  .panel { padding: 11px; }
  header { padding: 13px 14px; }
}
</style>
</head>
<body>
<header>
  <h1>Edytor geometrii rzutu</h1>
  <p id="project-title">Electrical Floorplan Engine · edycja lokalna</p>
</header>
<main>
  <section class="panel" aria-labelledby="tools-title">
    <h2 id="tools-title">Narzędzia</h2>
    <p class="muted">Kliknij punkty bezpośrednio na skalibrowanym podkładzie. Model zapisuje współrzędne w milimetrach, niezależnie od powiększenia obrazu.</p>
    <div class="button-row" role="group" aria-label="Tryb edytora">
      <button type="button" data-tool="select" aria-pressed="true">Zaznacz / przesuń</button>
      <button type="button" data-tool="wall" aria-pressed="false">Ściana</button>
      <button type="button" data-tool="room" aria-pressed="false">Pomieszczenie</button>
      <button type="button" data-tool="opening" aria-pressed="false">Otwór</button>
    </div>
    <div class="checkbox-row">
      <input id="snap-toggle" type="checkbox" checked>
      <label for="snap-toggle">Przyciągaj do końców ścian</label>
    </div>

    <h3>Parametry nowej ściany</h3>
    <div class="field"><label for="wall-role">Rola</label>
      <select id="wall-role">
        <option value="unknown">Nieokreślona</option><option value="exterior">Zewnętrzna</option>
        <option value="interior">Wewnętrzna</option><option value="partition">Działowa</option>
      </select>
    </div>
    <div class="field"><label for="wall-thickness">Grubość (mm, opcjonalnie)</label>
      <input id="wall-thickness" type="number" min="1" step="any" placeholder="np. 120">
    </div>

    <h3>Parametry pomieszczenia</h3>
    <div class="field"><label for="room-name">Nazwa pomieszczenia</label>
      <input id="room-name" maxlength="80" placeholder="np. Salon">
    </div>
    <div class="button-row">
      <button type="button" id="finish-room" disabled>Zamknij obrys</button>
      <button type="button" id="cancel-draft">Anuluj szkic</button>
    </div>

    <h3>Parametry otworu</h3>
    <div class="field"><label for="opening-wall">Ściana gospodarza</label><select id="opening-wall"></select></div>
    <div class="field"><label for="opening-kind">Rodzaj otworu</label>
      <select id="opening-kind">
        <option value="door">Drzwi</option><option value="window">Okno</option>
        <option value="passage">Przejście</option><option value="generic">Inny</option>
      </select>
    </div>
    <div class="field"><label for="opening-label">Etykieta (opcjonalnie)</label><input id="opening-label" maxlength="80" placeholder="np. D1"></div>
    <div class="field" id="sill-field"><label for="sill-height">Wysokość parapetu okna (mm, opcjonalnie)</label><input id="sill-height" type="number" min="0" step="any" placeholder="np. 900"></div>
    <p class="muted">Otwór utworzysz, wskazując dwa punkty wzdłuż wybranej ściany. Edytor rzutuje je na oś ściany i oblicza offset oraz szerokość.</p>

    <h3>Zaznaczony obiekt</h3>
    <div id="selected-info" class="status" aria-live="polite">Brak zaznaczonego obiektu.</div>
    <div class="field"><label for="selected-name">Nazwa / etykieta</label><input id="selected-name" maxlength="80" placeholder="Nazwa pomieszczenia lub etykieta"></div>
    <div class="field"><label for="selected-role">Rola ściany</label>
      <select id="selected-role">
        <option value="unknown">Nieokreślona</option><option value="exterior">Zewnętrzna</option>
        <option value="interior">Wewnętrzna</option><option value="partition">Działowa</option>
      </select>
    </div>
    <div class="field"><label for="selected-thickness">Grubość ściany (mm)</label><input id="selected-thickness" type="number" min="1" step="any"></div>
    <div class="field"><label for="selected-kind">Rodzaj otworu</label>
      <select id="selected-kind"><option value="door">Drzwi</option><option value="window">Okno</option><option value="passage">Przejście</option><option value="generic">Inny</option></select>
    </div>
    <div class="button-row">
      <button type="button" id="apply-properties" disabled>Zastosuj właściwości</button>
      <button type="button" id="delete-selected" class="danger" disabled>Usuń obiekt</button>
    </div>

    <h3>Historia i eksport</h3>
    <div class="button-row">
      <button type="button" id="undo" disabled>Cofnij</button>
      <button type="button" id="fit-view">Dopasuj widok</button>
      <button type="button" id="zoom-out" aria-label="Pomniejsz obraz">−</button>
      <button type="button" id="zoom-in" aria-label="Powiększ obraz">+</button>
    </div>
    <div id="message" class="status" role="status" aria-live="polite">Edytor działa lokalnie. Dane nie są wysyłane do sieci.</div>
    <button type="button" id="export-json" class="primary" style="margin-top:9px">Waliduj i pobierz JSON</button>
    <p class="muted">Eksport odrzuca powtórzone identyfikatory, nieprawidłowe ściany, samoprzecinające się pomieszczenia i otwory wykraczające poza ściany. Przed PDF uruchom również <code>floorplan-engine check</code>.</p>
    <h3>Elementy projektu</h3>
    <ul id="object-list"></ul>
  </section>
  <section class="panel" aria-labelledby="image-title">
    <div class="toolbar">
      <h2 id="image-title">Skalibrowany podkład</h2>
      <span class="muted" id="image-info">Wczytywanie obrazu…</span>
    </div>
    <div id="viewer" aria-label="Podkład rzutu i edytowalna geometria">
      <div id="stage">
        <img id="plan-image" alt="Skalibrowany rzut źródłowy">
        <svg id="overlay" role="img" aria-label="Warstwy geometrii; klikaj lub przeciągaj uchwyty"></svg>
      </div>
    </div>
    <div class="legend">
      <span><i class="dot" style="background:#154b73"></i>Ściany</span>
      <span><i class="dot" style="background:#14804a"></i>Pomieszczenia</span>
      <span><i class="dot" style="background:#c54c21"></i>Otwory</span>
      <span><i class="dot" style="background:#c51f4a"></i>Symbole elektryczne</span>
      <span><i class="dot" style="background:#e6a700"></i>Uchwyty edycji</span>
    </div>
  </section>
</main>
<script>
"use strict";
const EMBEDDED_IMAGE = "__IMAGE_DATA_URI__";
const PROJECT_BASE64 = "__PROJECT_BASE64__";
const SOURCE_NAME_BASE64 = "__SOURCE_NAME_BASE64__";

function decodeBase64(text) {
  const binary = atob(text);
  const bytes = Uint8Array.from(binary, character => character.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}
const embeddedProject = JSON.parse(decodeBase64(PROJECT_BASE64));
let project = {
  ...embeddedProject,
  walls: Array.isArray(embeddedProject.walls) ? embeddedProject.walls : [],
  openings: Array.isArray(embeddedProject.openings) ? embeddedProject.openings : [],
  rooms: Array.isArray(embeddedProject.rooms) ? embeddedProject.rooms : [],
  symbols: Array.isArray(embeddedProject.symbols) ? embeddedProject.symbols : []
};
const sourceName = decodeBase64(SOURCE_NAME_BASE64);
const image = document.getElementById("plan-image");
const overlay = document.getElementById("overlay");
const stage = document.getElementById("stage");
const viewer = document.getElementById("viewer");
const message = document.getElementById("message");
const wallSelect = document.getElementById("opening-wall");
const finishRoomButton = document.getElementById("finish-room");
const undoButton = document.getElementById("undo");
const deleteButton = document.getElementById("delete-selected");
const applyButton = document.getElementById("apply-properties");
let tool = "select";
let zoom = 1;
let naturalWidth = 0;
let naturalHeight = 0;
let draftPoints = [];
let openingPoints = [];
let wallFirstPoint = null;
let selected = null;
let dragging = null;
let suppressNextClick = false;
const undoStack = [];
const MAX_UNDO = 60;
const scale = Number(project.image_mm_per_pixel);
const originX = Number(project.image_origin_pixel_x || 0);
const originY = Number(project.image_origin_pixel_y || 0);

document.getElementById("project-title").textContent =
  (project.title || "Projekt") + " · edytor geometrii lokalnie";
image.alt = "Rzut: " + sourceName;
image.src = EMBEDDED_IMAGE;
document.getElementById("sill-field").hidden = false;

function clone(value) { return JSON.parse(JSON.stringify(value)); }
function allObjects() {
  return [
    ...project.walls.map(item => ({ type: "wall", item })),
    ...project.openings.map(item => ({ type: "opening", item })),
    ...project.rooms.map(item => ({ type: "room", item })),
    ...project.symbols.map(item => ({ type: "symbol", item }))
  ];
}
function objectById(id) { return allObjects().find(entry => entry.item.id === id) || null; }
function makeId(prefix) {
  const ids = new Set(allObjects().map(entry => entry.item.id));
  let next = 1;
  while (ids.has(prefix + "-" + next)) next += 1;
  return prefix + "-" + next;
}
function saveUndo() {
  undoStack.push(clone(project));
  if (undoStack.length > MAX_UNDO) undoStack.shift();
  undoButton.disabled = undoStack.length === 0;
}
function setMessage(text, kind) {
  message.textContent = text;
  message.classList.remove("error", "success");
  if (kind) message.classList.add(kind);
}
function pixelToModel(point) {
  return { x: (point.x - originX) * scale, y: (originY - point.y) * scale };
}
function modelToPixel(point) {
  return { x: point.x / scale + originX, y: originY - point.y / scale };
}
function pointOnWall(wall, t) {
  return { x: wall.start.x + (wall.end.x - wall.start.x) * t,
    y: wall.start.y + (wall.end.y - wall.start.y) * t };
}
function wallLength(wall) {
  return Math.hypot(wall.end.x - wall.start.x, wall.end.y - wall.start.y);
}
function projectOnWall(point, wall) {
  const dx = wall.end.x - wall.start.x;
  const dy = wall.end.y - wall.start.y;
  const denominator = dx * dx + dy * dy;
  if (denominator <= 1e-12) return 0;
  return Math.max(0, Math.min(1, ((point.x - wall.start.x) * dx + (point.y - wall.start.y) * dy) / denominator));
}
function openingPointsMm(opening, wall) {
  const length = wallLength(wall);
  return [
    pointOnWall(wall, opening.offset_mm / length),
    pointOnWall(wall, (opening.offset_mm + opening.width_mm) / length)
  ];
}
function svgElement(name, attrs, text) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(attrs || {}).forEach(([key, value]) => element.setAttribute(key, String(value)));
  if (text !== undefined) element.textContent = text;
  return element;
}
function addHandle(point, id, handle, index) {
  const p = modelToPixel(point);
  const element = svgElement("circle", {
    cx: p.x, cy: p.y, r: 7 / zoom, fill: "#e6a700", stroke: "white",
    "stroke-width": 2 / zoom, "data-object-id": id, "data-handle": handle,
    "data-index": index === undefined ? "" : index, class: "handle"
  });
  overlay.appendChild(element);
}
function render() {
  if (!naturalWidth) return;
  while (overlay.firstChild) overlay.removeChild(overlay.firstChild);
  overlay.setAttribute("viewBox", "0 0 " + naturalWidth + " " + naturalHeight);
  project.rooms.forEach(room => {
    const points = room.vertices.map(modelToPixel);
    overlay.appendChild(svgElement("polygon", {
      points: points.map(p => p.x + "," + p.y).join(" "),
      fill: "rgba(20,128,74,0.16)", stroke: selected && selected.id === room.id ? "#e6a700" : "#14804a",
      "stroke-width": (selected && selected.id === room.id ? 3 : 2) / zoom,
      "data-object-id": room.id
    }));
    const label = room.label_position || {
      x: room.vertices.reduce((sum, p) => sum + p.x, 0) / room.vertices.length,
      y: room.vertices.reduce((sum, p) => sum + p.y, 0) / room.vertices.length
    };
    const lp = modelToPixel(label);
    overlay.appendChild(svgElement("text", {
      x: lp.x, y: lp.y, "font-size": 14 / zoom, "font-weight": 700, fill: "#12663b",
      "text-anchor": "middle", "pointer-events": "none", "data-object-id": room.id
    }, room.name));
  });
  project.walls.forEach(wall => {
    const a = modelToPixel(wall.start);
    const b = modelToPixel(wall.end);
    const thickness = Number(wall.thickness_mm || 80);
    const width = Math.max(2 / zoom, Math.min(13 / zoom, thickness / scale * 0.2));
    overlay.appendChild(svgElement("line", {
      x1: a.x, y1: a.y, x2: b.x, y2: b.y, stroke: selected && selected.id === wall.id ? "#e6a700" : "#154b73",
      "stroke-width": width, "stroke-linecap": "round", "data-object-id": wall.id
    }));
  });
  project.openings.forEach(opening => {
    const wall = project.walls.find(item => item.id === opening.wall_id);
    if (!wall) return;
    const endpoints = openingPointsMm(opening, wall).map(modelToPixel);
    const wallWidth = Math.max(4 / zoom, Math.min(16 / zoom, Number(wall.thickness_mm || 80) / scale * 0.2 + 4 / zoom));
    overlay.appendChild(svgElement("line", {
      x1: endpoints[0].x, y1: endpoints[0].y, x2: endpoints[1].x, y2: endpoints[1].y,
      stroke: "#ffffff", "stroke-width": wallWidth, "stroke-linecap": "butt",
      "data-object-id": opening.id
    }));
    if (opening.kind === "window") {
      overlay.appendChild(svgElement("line", {
        x1: endpoints[0].x, y1: endpoints[0].y, x2: endpoints[1].x, y2: endpoints[1].y,
        stroke: selected && selected.id === opening.id ? "#e6a700" : "#c54c21",
        "stroke-width": 2 / zoom, "data-object-id": opening.id
      }));
    } else {
      const mid = { x: (endpoints[0].x + endpoints[1].x) / 2, y: (endpoints[0].y + endpoints[1].y) / 2 };
      overlay.appendChild(svgElement("circle", {
        cx: mid.x, cy: mid.y, r: 3.5 / zoom, fill: selected && selected.id === opening.id ? "#e6a700" : "#c54c21",
        "data-object-id": opening.id
      }));
    }
    if (opening.label) {
      const mid = { x: (endpoints[0].x + endpoints[1].x) / 2, y: (endpoints[0].y + endpoints[1].y) / 2 };
      overlay.appendChild(svgElement("text", {
        x: mid.x, y: mid.y - 8 / zoom, "font-size": 11 / zoom, fill: "#9e3418",
        "text-anchor": "middle", "pointer-events": "none", "data-object-id": opening.id
      }, opening.label));
    }
  });
  project.symbols.forEach(symbol => {
    const p = modelToPixel(symbol.position);
    overlay.appendChild(svgElement("circle", {
      cx: p.x, cy: p.y, r: 5 / zoom, fill: "#c51f4a", stroke: "white",
      "stroke-width": 1.5 / zoom, "data-object-id": symbol.id
    }));
    if (symbol.label) overlay.appendChild(svgElement("text", {
      x: p.x + 7 / zoom, y: p.y - 7 / zoom, "font-size": 11 / zoom, fill: "#98163a",
      "pointer-events": "none", "data-object-id": symbol.id
    }, symbol.label));
  });
  if (tool === "wall" && wallFirstPoint) {
    const p = modelToPixel(wallFirstPoint);
    overlay.appendChild(svgElement("circle", { cx: p.x, cy: p.y, r: 6 / zoom, fill: "#e6a700" }));
  }
  if (tool === "room" && draftPoints.length) {
    const pixels = draftPoints.map(modelToPixel);
    overlay.appendChild(svgElement("polyline", {
      points: pixels.map(p => p.x + "," + p.y).join(" "), fill: "none",
      stroke: "#e6a700", "stroke-width": 2 / zoom, "stroke-dasharray": 7 / zoom + " " + 5 / zoom
    }));
    pixels.forEach(p => overlay.appendChild(svgElement("circle", {
      cx: p.x, cy: p.y, r: 5 / zoom, fill: "#e6a700"
    })));
  }
  if (tool === "opening" && openingPoints.length) {
    const pixels = openingPoints.map(modelToPixel);
    pixels.forEach(p => overlay.appendChild(svgElement("circle", { cx: p.x, cy: p.y, r: 5 / zoom, fill: "#c54c21" })));
    if (pixels.length === 2) overlay.appendChild(svgElement("line", {
      x1: pixels[0].x, y1: pixels[0].y, x2: pixels[1].x, y2: pixels[1].y,
      stroke: "#c54c21", "stroke-width": 2 / zoom, "stroke-dasharray": 5 / zoom + " " + 4 / zoom
    }));
  }
  if (selected && tool === "select") {
    const found = objectById(selected.id);
    if (found && found.type === "wall") {
      addHandle(found.item.start, found.item.id, "wall-start");
      addHandle(found.item.end, found.item.id, "wall-end");
    } else if (found && found.type === "room") {
      found.item.vertices.forEach((p, index) => addHandle(p, found.item.id, "room-vertex", index));
    } else if (found && found.type === "opening") {
      const wall = project.walls.find(item => item.id === found.item.wall_id);
      if (wall) openingPointsMm(found.item, wall).forEach((p, index) =>
        addHandle(p, found.item.id, index === 0 ? "opening-start" : "opening-end", index));
    }
  }
  renderObjectList();
  updateSelectionPanel();
  finishRoomButton.disabled = tool !== "room" || draftPoints.length < 3;
}
function renderObjectList() {
  const list = document.getElementById("object-list");
  while (list.firstChild) list.removeChild(list.firstChild);
  allObjects().forEach(({ type, item }) => {
    const row = document.createElement("li");
    row.textContent = type + ": " + item.id + (item.name ? " · " + item.name : item.label ? " · " + item.label : "");
    list.appendChild(row);
  });
  if (!list.childElementCount) {
    const row = document.createElement("li");
    row.textContent = "Brak obiektów — dodaj ściany, pomieszczenia lub otwory.";
    list.appendChild(row);
  }
}
function updateSelectionPanel() {
  const info = document.getElementById("selected-info");
  const name = document.getElementById("selected-name");
  const role = document.getElementById("selected-role");
  const thickness = document.getElementById("selected-thickness");
  const kind = document.getElementById("selected-kind");
  const found = selected ? objectById(selected.id) : null;
  applyButton.disabled = !found;
  deleteButton.disabled = !found;
  if (!found) {
    info.textContent = "Brak zaznaczonego obiektu.";
    name.value = ""; thickness.value = "";
    return;
  }
  const item = found.item;
  info.textContent = found.type + " · " + item.id;
  name.value = found.type === "room" ? item.name : (item.label || "");
  role.disabled = found.type !== "wall";
  thickness.disabled = found.type !== "wall";
  kind.disabled = found.type !== "opening";
  role.value = item.role || "unknown";
  thickness.value = item.thickness_mm == null ? "" : item.thickness_mm;
  kind.value = item.kind || "door";
}
function selectTool(next) {
  tool = next;
  document.querySelectorAll("[data-tool]").forEach(button =>
    button.setAttribute("aria-pressed", String(button.dataset.tool === tool)));
  const descriptions = {
    select: "Zaznacz obiekt. Przeciągnij żółte uchwyty, aby zmienić geometrię.",
    wall: "Kliknij początek i koniec nowej ściany.",
    room: "Klikaj wierzchołki pomieszczenia, a następnie wybierz „Zamknij obrys”.",
    opening: "Wybierz ścianę gospodarza i kliknij dwa punkty wzdłuż jej osi."
  };
  setMessage(descriptions[tool]);
  draftPoints = [];
  openingPoints = [];
  wallFirstPoint = null;
  render();
}
document.querySelectorAll("[data-tool]").forEach(button =>
  button.addEventListener("click", () => selectTool(button.dataset.tool)));
function refreshWallOptions() {
  const current = wallSelect.value;
  while (wallSelect.firstChild) wallSelect.removeChild(wallSelect.firstChild);
  project.walls.forEach(wall => {
    const option = document.createElement("option");
    option.value = wall.id;
    option.textContent = wall.id;
    wallSelect.appendChild(option);
  });
  if (project.walls.some(wall => wall.id === current)) wallSelect.value = current;
  if (!project.walls.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "Najpierw dodaj ścianę";
    wallSelect.appendChild(option);
  }
}
function imagePoint(event) {
  const rect = overlay.getBoundingClientRect();
  return {
    x: Math.max(0, Math.min(naturalWidth, (event.clientX - rect.left) * naturalWidth / rect.width)),
    y: Math.max(0, Math.min(naturalHeight, (event.clientY - rect.top) * naturalHeight / rect.height))
  };
}
function snapPoint(point) {
  if (!document.getElementById("snap-toggle").checked) return point;
  let closest = null;
  let distance = 10 / zoom;
  project.walls.forEach(wall => [wall.start, wall.end].forEach(endpoint => {
    const pixel = modelToPixel(endpoint);
    const nextDistance = Math.hypot(point.x - pixel.x, point.y - pixel.y);
    if (nextDistance < distance) { distance = nextDistance; closest = pixel; }
  }));
  return closest || point;
}
function createWall(pointA, pointB) {
  if (Math.hypot(pointB.x - pointA.x, pointB.y - pointA.y) < 1) {
    setMessage("Ściana musi mieć dodatnią długość.", "error"); return;
  }
  const thicknessRaw = document.getElementById("wall-thickness").value;
  const thickness = thicknessRaw === "" ? null : Number(thicknessRaw);
  if (thickness !== null && (!Number.isFinite(thickness) || thickness <= 0)) {
    setMessage("Grubość ściany musi być dodatnia.", "error"); return;
  }
  saveUndo();
  const wall = {
    id: makeId("wall"), start: pointA, end: pointB,
    role: document.getElementById("wall-role").value
  };
  if (thickness !== null) wall.thickness_mm = thickness;
  project.walls.push(wall);
  selected = { id: wall.id };
  refreshWallOptions();
  render();
  setMessage("Dodano ścianę " + wall.id + ".", "success");
}
function finishRoom() {
  if (draftPoints.length < 3) {
    setMessage("Pomieszczenie wymaga co najmniej trzech wierzchołków.", "error"); return;
  }
  const name = document.getElementById("room-name").value.trim();
  if (!name) { setMessage("Wpisz nazwę pomieszczenia przed zamknięciem obrysu.", "error"); return; }
  if (!validRoom(draftPoints)) {
    setMessage("Obrys pomieszczenia ma zerowe pole lub przecina sam siebie.", "error"); return;
  }
  saveUndo();
  const room = { id: makeId("room"), name, vertices: clone(draftPoints) };
  project.rooms.push(room);
  selected = { id: room.id };
  draftPoints = [];
  selectTool("select");
  setMessage("Dodano pomieszczenie " + room.name + ".", "success");
}
finishRoomButton.addEventListener("click", finishRoom);
function addOpening(pointA, pointB) {
  const wall = project.walls.find(item => item.id === wallSelect.value);
  if (!wall) { setMessage("Wybierz istniejącą ścianę gospodarza.", "error"); return; }
  const length = wallLength(wall);
  if (!(length > 0)) { setMessage("Ściana gospodarza jest nieprawidłowa.", "error"); return; }
  const firstT = projectOnWall(pointA, wall);
  const secondT = projectOnWall(pointB, wall);
  const offset = Math.min(firstT, secondT) * length;
  const width = Math.abs(secondT - firstT) * length;
  if (width < 1) { setMessage("Szerokość otworu musi być dodatnia.", "error"); return; }
  const kind = document.getElementById("opening-kind").value;
  const label = document.getElementById("opening-label").value.trim();
  const sillRaw = document.getElementById("sill-height").value;
  const sill = sillRaw === "" ? null : Number(sillRaw);
  if (kind !== "window" && sill !== null) {
    setMessage("Wysokość parapetu jest dozwolona tylko dla okna.", "error"); return;
  }
  if (sill !== null && (!Number.isFinite(sill) || sill < 0)) {
    setMessage("Wysokość parapetu nie może być ujemna.", "error"); return;
  }
  saveUndo();
  const opening = {
    id: makeId("opening"), wall_id: wall.id, kind, offset_mm: offset, width_mm: width,
    hinge_at: "start", swing_side: "left"
  };
  if (label) opening.label = label;
  if (sill !== null) opening.sill_height_mm = sill;
  project.openings.push(opening);
  selected = { id: opening.id };
  openingPoints = [];
  refreshWallOptions();
  selectTool("select");
  setMessage("Dodano otwór " + opening.id + " (" + width.toFixed(1) + " mm).", "success");
}
function handleCanvasClick(event) {
  if (suppressNextClick) { suppressNextClick = false; return; }
  if (!naturalWidth || dragging) return;
  const targetObject = event.target.closest("[data-object-id]");
  const targetHandle = event.target.closest("[data-handle]");
  if (tool === "select") {
    selected = targetObject ? { id: targetObject.getAttribute("data-object-id") } : null;
    render();
    return;
  }
  if (targetHandle) return;
  const px = snapPoint(imagePoint(event));
  const mm = pixelToModel(px);
  if (tool === "wall") {
    if (!wallFirstPoint) {
      wallFirstPoint = mm;
      render();
      setMessage("Wskaż drugi koniec ściany.");
    } else {
      const first = wallFirstPoint;
      wallFirstPoint = null;
      createWall(first, mm);
    }
  } else if (tool === "room") {
    draftPoints.push(mm);
    render();
    setMessage("Wierzchołki pomieszczenia: " + draftPoints.length + ". Zamknij obrys po wskazaniu ostatniego punktu.");
  } else if (tool === "opening") {
    const wall = project.walls.find(item => item.id === wallSelect.value);
    if (!wall) { setMessage("Najpierw narysuj ścianę i wybierz ją na liście.", "error"); return; }
    openingPoints.push(mm);
    if (openingPoints.length === 1) {
      render();
      setMessage("Wskaż drugi koniec otworu na ścianie " + wall.id + ".");
    } else {
      const first = openingPoints[0];
      openingPoints = [];
      addOpening(first, mm);
    }
  }
}
overlay.addEventListener("click", handleCanvasClick);
function clamp(value, minimum, maximum) { return Math.max(minimum, Math.min(maximum, value)); }
overlay.addEventListener("pointerdown", event => {
  const handle = event.target.closest("[data-handle]");
  if (!handle || tool !== "select") return;
  const id = handle.getAttribute("data-object-id");
  const found = objectById(id);
  if (!found) return;
  const handleName = handle.getAttribute("data-handle");
  const indexText = handle.getAttribute("data-index");
  const index = indexText === "" ? null : Number(indexText);
  selected = { id };
  dragging = { id, type: found.type, handle: handleName, index, moved: false, before: clone(project) };
  if (found.type === "opening") {
    const wall = project.walls.find(item => item.id === found.item.wall_id);
    dragging.wallId = wall.id;
    dragging.wallLength = wallLength(wall);
    dragging.startT = found.item.offset_mm / dragging.wallLength;
    dragging.endT = (found.item.offset_mm + found.item.width_mm) / dragging.wallLength;
  }
  overlay.setPointerCapture(event.pointerId);
  event.preventDefault();
});
overlay.addEventListener("pointermove", event => {
  if (!dragging) return;
  const found = objectById(dragging.id);
  if (!found) return;
  if (!dragging.moved) {
    undoStack.push(dragging.before);
    if (undoStack.length > MAX_UNDO) undoStack.shift();
    undoButton.disabled = false;
  }
  const modelPoint = pixelToModel(imagePoint(event));
  if (dragging.type === "wall") {
    found.item[dragging.handle === "wall-start" ? "start" : "end"] = modelPoint;
  } else if (dragging.type === "room") {
    found.item.vertices[dragging.index] = modelPoint;
  } else if (dragging.type === "opening") {
    const wall = project.walls.find(item => item.id === dragging.wallId);
    const t = projectOnWall(modelPoint, wall);
    const fixedT = dragging.handle === "opening-start" ? dragging.endT : dragging.startT;
    const startT = Math.min(t, fixedT);
    const endT = Math.max(t, fixedT);
    found.item.offset_mm = startT * dragging.wallLength;
    found.item.width_mm = Math.max(0.5, (endT - startT) * dragging.wallLength);
  }
  dragging.moved = true;
  render();
});
function endDrag() {
  if (!dragging) return;
  const moved = dragging.moved;
  dragging = null;
  suppressNextClick = moved;
  render();
  setMessage(moved ? "Geometria zmieniona. Przed eksportem zweryfikuj komunikaty walidacji." : "Zaznaczono uchwyt.");
}
overlay.addEventListener("pointerup", endDrag);
overlay.addEventListener("pointercancel", endDrag);

function deleteSelected() {
  if (!selected) return;
  const id = selected.id;
  const found = objectById(id);
  if (!found) return;
  saveUndo();
  if (found.type === "wall") {
    const dependent = project.openings.filter(item => item.wall_id === id).length;
    project.walls = project.walls.filter(item => item.id !== id);
    project.openings = project.openings.filter(item => item.wall_id !== id);
    setMessage(dependent ? "Usunięto ścianę i " + dependent + " przypisanych otworów." : "Usunięto ścianę.", "success");
  } else {
    const collection = found.type === "room" ? "rooms" : found.type === "opening" ? "openings" : "symbols";
    project[collection] = project[collection].filter(item => item.id !== id);
    setMessage("Usunięto obiekt " + id + ".", "success");
  }
  selected = null;
  refreshWallOptions();
  render();
}
deleteButton.addEventListener("click", deleteSelected);
document.getElementById("cancel-draft").addEventListener("click", () => {
  draftPoints = [];
  openingPoints = [];
  wallFirstPoint = null;
  render();
  setMessage("Anulowano bieżący szkic.");
});
undoButton.addEventListener("click", () => {
  if (!undoStack.length) return;
  project = undoStack.pop();
  undoButton.disabled = undoStack.length === 0;
  selected = null;
  dragging = null;
  refreshWallOptions();
  render();
  setMessage("Cofnięto ostatnią zmianę.");
});

applyButton.addEventListener("click", () => {
  if (!selected) return;
  const found = objectById(selected.id);
  if (!found) return;
  const name = document.getElementById("selected-name").value.trim();
  const role = document.getElementById("selected-role").value;
  const thicknessRaw = document.getElementById("selected-thickness").value;
  const kind = document.getElementById("selected-kind").value;
  if ((found.type === "room" && !name) || name.length > 80) {
    setMessage("Nazwa pomieszczenia nie może być pusta ani dłuższa niż 80 znaków.", "error"); return;
  }
  if (found.type === "wall" && thicknessRaw !== "" && !(Number(thicknessRaw) > 0)) {
    setMessage("Grubość ściany musi być dodatnia.", "error"); return;
  }
  saveUndo();
  if (found.type === "room") found.item.name = name;
  if (found.type === "opening") {
    found.item.label = name || null;
    found.item.kind = kind;
    if (kind !== "window") delete found.item.sill_height_mm;
  }
  if (found.type === "wall") {
    found.item.role = role;
    if (thicknessRaw === "") delete found.item.thickness_mm;
    else found.item.thickness_mm = Number(thicknessRaw);
  }
  if (found.type === "symbol") found.item.label = name || null;
  render();
  setMessage("Zaktualizowano właściwości obiektu.", "success");
});

document.getElementById("zoom-in").addEventListener("click", () => { zoom = Math.min(8, zoom * 1.25); applyZoom(); });
document.getElementById("zoom-out").addEventListener("click", () => { zoom = Math.max(0.03, zoom / 1.25); applyZoom(); });
document.getElementById("fit-view").addEventListener("click", fitZoom);
function fitZoom() {
  if (!naturalWidth) return;
  zoom = Math.min(1, Math.max(200, viewer.clientWidth - 24) / naturalWidth);
  applyZoom();
}
function applyZoom() {
  if (!naturalWidth) return;
  stage.style.width = Math.max(1, Math.round(naturalWidth * zoom)) + "px";
  stage.style.height = Math.max(1, Math.round(naturalHeight * zoom)) + "px";
  render();
}
image.addEventListener("load", () => {
  naturalWidth = image.naturalWidth;
  naturalHeight = image.naturalHeight;
  if (!naturalWidth || !naturalHeight) {
    setMessage("Nie udało się odczytać wymiarów obrazu.", "error"); return;
  }
  document.getElementById("image-info").textContent = sourceName + " · " + naturalWidth + " × " + naturalHeight + " px · " + scale + " mm/px";
  refreshWallOptions();
  fitZoom();
});
image.addEventListener("error", () => setMessage("Nie można odczytać osadzonego obrazu źródłowego.", "error"));
window.addEventListener("resize", () => { if (naturalWidth && zoom < 1) fitZoom(); });

function cross(a, b, c) { return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x); }
function onSegment(a, b, p) {
  const e = 1e-7;
  return p.x >= Math.min(a.x, b.x) - e && p.x <= Math.max(a.x, b.x) + e &&
    p.y >= Math.min(a.y, b.y) - e && p.y <= Math.max(a.y, b.y) + e;
}
function segmentsIntersect(a, b, c, d) {
  const abC = cross(a, b, c), abD = cross(a, b, d), cdA = cross(c, d, a), cdB = cross(c, d, b);
  if (((abC > 1e-7 && abD < -1e-7) || (abC < -1e-7 && abD > 1e-7)) &&
      ((cdA > 1e-7 && cdB < -1e-7) || (cdA < -1e-7 && cdB > 1e-7))) return true;
  return (Math.abs(abC) <= 1e-7 && onSegment(a, b, c)) ||
    (Math.abs(abD) <= 1e-7 && onSegment(a, b, d)) ||
    (Math.abs(cdA) <= 1e-7 && onSegment(c, d, a)) ||
    (Math.abs(cdB) <= 1e-7 && onSegment(c, d, b));
}
function validRoom(vertices) {
  if (!Array.isArray(vertices) || vertices.length < 3) return false;
  const unique = new Set(vertices.map(p => p.x + "," + p.y));
  if (unique.size !== vertices.length) return false;
  const area2 = vertices.reduce((area, p, i) => {
    const q = vertices[(i + 1) % vertices.length];
    return area + p.x * q.y - q.x * p.y;
  }, 0);
  if (Math.abs(area2) < 1e-7) return false;
  for (let i = 0; i < vertices.length; i++) {
    for (let j = i + 1; j < vertices.length; j++) {
      if (j === i + 1 || (i === 0 && j === vertices.length - 1)) continue;
      if (segmentsIntersect(vertices[i], vertices[(i + 1) % vertices.length], vertices[j], vertices[(j + 1) % vertices.length])) return false;
    }
  }
  return true;
}
function validateProject() {
  const errors = [];
  const objects = allObjects();
  const ids = objects.map(entry => entry.item.id);
  if (ids.some(id => !id) || new Set(ids).size !== ids.length) errors.push("Identyfikatory obiektów muszą być niepuste i unikalne.");
  for (const wall of project.walls) {
    if (!wall.start || !wall.end || !Number.isFinite(wall.start.x) || !Number.isFinite(wall.start.y) ||
        !Number.isFinite(wall.end.x) || !Number.isFinite(wall.end.y) || wallLength(wall) <= 1e-7) {
      errors.push("Ściana " + wall.id + " ma nieprawidłową lub zerową długość.");
    }
  }
  for (const room of project.rooms) {
    if (!room.name || room.name.length > 80 || !validRoom(room.vertices)) errors.push("Pomieszczenie " + room.id + " ma nieprawidłowy obrys lub nazwę.");
  }
  for (const opening of project.openings) {
    const wall = project.walls.find(item => item.id === opening.wall_id);
    if (!wall) { errors.push("Otwór " + opening.id + " wskazuje nieistniejącą ścianę."); continue; }
    const length = wallLength(wall);
    if (!Number.isFinite(opening.offset_mm) || !Number.isFinite(opening.width_mm) ||
        opening.offset_mm < 0 || opening.width_mm <= 0 || opening.offset_mm + opening.width_mm > length + 1e-6) {
      errors.push("Otwór " + opening.id + " wykracza poza ścianę lub ma nieprawidłowe wymiary.");
    }
  }
  const grouped = new Map();
  project.openings.forEach(opening => {
    if (!grouped.has(opening.wall_id)) grouped.set(opening.wall_id, []);
    grouped.get(opening.wall_id).push(opening);
  });
  grouped.forEach((openings, wallId) => {
    openings.sort((a, b) => a.offset_mm - b.offset_mm);
    for (let i = 1; i < openings.length; i++) {
      if (openings[i].offset_mm < openings[i - 1].offset_mm + openings[i - 1].width_mm - 1e-7) {
        errors.push("Otwory " + openings[i - 1].id + " i " + openings[i].id + " nakładają się na ścianie " + wallId + ".");
      }
    }
  });
  return errors;
}
document.getElementById("export-json").addEventListener("click", () => {
  const errors = validateProject();
  if (errors.length) {
    setMessage("Eksport przerwany — popraw błędy:\n" + errors.join("\n"), "error"); return;
  }
  const output = JSON.stringify(project, null, 2) + "\n";
  const blob = new Blob([output], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  const safeTitle = String(project.title || "plan").normalize("NFKD")
    .replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-+|-+$/g, "") || "plan";
  anchor.download = safeTitle + ".geometry.json";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  setMessage("Walidacja lokalna zakończona. Pobrano plik " + anchor.download + ".", "success");
});
refreshWallOptions();
render();
</script>
</body>
</html>
"""


def create_geometry_ui(project_path: str | Path, output_path: str | Path | None = None) -> Path:
    """Build a self-contained geometry editor from a calibrated project JSON and raster."""
    project_file = Path(project_path).resolve()
    raw = json.loads(project_file.read_text(encoding="utf-8"))
    project = FloorplanProject.model_validate(raw)
    if not project.source_image or project.image_mm_per_pixel is None:
        raise ValueError("Project must define source_image and image_mm_per_pixel calibration.")

    image_path = Path(project.source_image)
    if not image_path.is_absolute():
        image_path = (project_file.parent / image_path).resolve()
    if not image_path.is_file():
        raise FileNotFoundError(f"Source image does not exist: {image_path}")

    mime_type, _ = mimetypes.guess_type(image_path.name)
    if not mime_type or not mime_type.startswith("image/"):
        raise ValueError(f"Cannot determine image MIME type for {image_path.name!r}")

    image_payload = base64.b64encode(image_path.read_bytes()).decode("ascii")
    image_data_uri = f"data:{mime_type};base64,{image_payload}"
    project_payload = base64.b64encode(json.dumps(raw, ensure_ascii=False).encode("utf-8")).decode("ascii")
    source_payload = base64.b64encode(image_path.name.encode("utf-8")).decode("ascii")
    html = (
        _HTML_TEMPLATE.replace("__IMAGE_DATA_URI__", image_data_uri)
        .replace("__PROJECT_BASE64__", project_payload)
        .replace("__SOURCE_NAME_BASE64__", source_payload)
    )

    output = (
        Path(output_path)
        if output_path is not None
        else project_file.with_name(f"{project_file.stem}.geometry.html")
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return output
