"""Local HTTP backend for editing calibrated floorplan projects."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import ValidationError

from electrical_floorplan_engine.geometry_ui import build_geometry_html
from electrical_floorplan_engine.models import FloorplanProject

_PROJECT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_INDEX_HTML = """<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Electrical Floorplan Engine — projekty</title>
<style>
:root { color-scheme: light; font-family: system-ui, sans-serif; color: #17212b;
        background: #f3f5f7; }
body { max-width: 900px; margin: 0 auto; padding: 24px; }
h1 { margin-bottom: 6px; } p { line-height: 1.5; }
ul { list-style: none; margin: 20px 0; padding: 0; display: grid; gap: 10px; }
li { background: white; border: 1px solid #d9e0e6; border-radius: 10px; padding: 14px; }
a { color: #125b91; font-weight: 700; }
.status { color: #52616e; } .error { color: #912d25; }
code { overflow-wrap: anywhere; }
</style>
</head>
<body>
<h1>Electrical Floorplan Engine</h1>
<p>Wybierz skalibrowany projekt z katalogu roboczego backendu. Zapis z edytora trafia
   do pliku JSON na serwerze.</p>
<p id="status" class="status" role="status" aria-live="polite">Wczytywanie projektów…</p>
<ul id="projects"></ul>
<p class="status">Aby dodać projekt, skopiuj plik JSON oraz obraz źródłowy do katalogu
roboczego, a następnie odśwież tę stronę.</p>
<script>
"use strict";
(async () => {
  const status = document.getElementById("status");
  const list = document.getElementById("projects");
  try {
    const response = await fetch("/api/projects", { cache: "no-store" });
    if (!response.ok) throw new Error("API zwróciło HTTP " + response.status);
    const projects = await response.json();
    list.replaceChildren();
    if (!projects.length) {
      status.textContent = "Brak plików JSON w katalogu roboczym backendu.";
      return;
    }
    let editableCount = 0;
    for (const project of projects) {
      const item = document.createElement("li");
      const title = document.createElement("strong");
      title.textContent = project.title || project.id;
      item.appendChild(title);
      item.appendChild(document.createElement("br"));
      const detail = document.createElement("small");
      detail.textContent = project.id + ".json";
      item.appendChild(detail);
      item.appendChild(document.createElement("br"));
      if (project.editable) {
        const link = document.createElement("a");
        link.href = "/editor/" + encodeURIComponent(project.id);
        link.textContent = "Otwórz edytor";
        item.appendChild(link);
        editableCount += 1;
      } else {
        const note = document.createElement("span");
        note.className = "error";
        note.textContent = project.reason || "Projekt nie jest gotowy do edycji.";
        item.appendChild(note);
      }
      list.appendChild(item);
    }
    status.textContent =
      "Projekty: " + projects.length + "; gotowe do edycji: " + editableCount + ".";
  } catch (error) {
    status.className = "status error";
    status.textContent = "Nie można wczytać projektów: " + error.message;
  }
})();
</script>
</body>
</html>
"""


def _revision(content: bytes) -> str:
    """Return the SHA-256 revision of the exact persisted file bytes."""
    return hashlib.sha256(content).hexdigest()


def create_app(workspace: str | Path) -> FastAPI:
    """Create a local project editor API rooted at a single workspace directory."""
    root = Path(workspace).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    app = FastAPI(
        title="Electrical Floorplan Engine",
        description="Local API for editing, validating, and saving calibrated floorplan projects.",
        version="0.1.0",
    )
    save_lock = threading.Lock()

    def project_path(project_id: str) -> Path:
        if not _PROJECT_ID.fullmatch(project_id) or ".." in project_id:
            raise HTTPException(status_code=404, detail="Project not found.")
        path = root / f"{project_id}.json"
        if not path.is_file() or path.resolve().parent != root:
            raise HTTPException(status_code=404, detail="Project not found.")
        return path

    def project_state(path: Path) -> tuple[FloorplanProject, bytes, str]:
        try:
            content = path.read_bytes()
            raw = json.loads(content)
            project = FloorplanProject.model_validate(raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
            raise HTTPException(
                status_code=422,
                detail="Project JSON is invalid or does not match the floorplan model.",
            ) from exc
        return project, content, _revision(content)

    def image_path(project: FloorplanProject, path: Path) -> tuple[Path, str]:
        if not project.source_image or project.image_mm_per_pixel is None:
            raise HTTPException(
                status_code=422,
                detail="The editor requires source_image and image_mm_per_pixel calibration.",
            )
        image = Path(project.source_image)
        if not image.is_absolute():
            image = path.parent / image
        try:
            image = image.resolve(strict=True)
        except OSError as exc:
            raise HTTPException(status_code=404, detail="Source image not found.") from exc
        if not image.is_relative_to(root) or not image.is_file():
            raise HTTPException(
                status_code=403,
                detail="Source image must be a file inside the configured workspace.",
            )
        mime_type, _ = mimetypes.guess_type(image.name)
        if not mime_type or not mime_type.startswith("image/") or mime_type == "image/svg+xml":
            raise HTTPException(
                status_code=415, detail="Source file must be a supported raster image."
            )
        return image, mime_type

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index() -> HTMLResponse:
        return HTMLResponse(_INDEX_HTML, headers={"Cache-Control": "no-store"})

    @app.get("/api/projects")
    def list_projects() -> list[dict[str, object]]:
        entries: list[dict[str, object]] = []
        for path in sorted(root.glob("*.json"), key=lambda candidate: candidate.name.casefold()):
            project_id = path.stem
            if not _PROJECT_ID.fullmatch(project_id) or ".." in project_id:
                continue
            item: dict[str, object] = {
                "id": project_id,
                "title": project_id,
                "editable": False,
                "reason": "Projekt nie jest gotowy do edycji.",
            }
            try:
                project, _, revision = project_state(project_path(project_id))
                image_path(project, path)
                item.update(
                    {
                        "title": project.title,
                        "editable": True,
                        "reason": None,
                        "revision": revision,
                    }
                )
            except HTTPException as exc:
                item["reason"] = str(exc.detail)
            except (OSError, ValueError):
                item["reason"] = "Nie można odczytać pliku projektu."
            entries.append(item)
        return entries

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str) -> dict[str, object]:
        path = project_path(project_id)
        project, _, revision = project_state(path)
        image_path(project, path)
        return {
            "id": project_id,
            "revision": revision,
            "project": project.model_dump(mode="json"),
        }

    @app.get("/api/projects/{project_id}/image", include_in_schema=False)
    def get_project_image(project_id: str) -> FileResponse:
        path = project_path(project_id)
        project, _, _ = project_state(path)
        source, mime_type = image_path(project, path)
        return FileResponse(
            source,
            media_type=mime_type,
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )

    @app.get("/editor/{project_id}", response_class=HTMLResponse, include_in_schema=False)
    def editor(project_id: str) -> HTMLResponse:
        path = project_path(project_id)
        project, _, revision = project_state(path)
        image_path(project, path)
        try:
            html = build_geometry_html(
                path,
                backend_project_id=project_id,
                image_url=f"/api/projects/{project_id}/image",
                revision=revision,
            )
        except (OSError, json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=422, detail="Cannot build editor for this project."
            ) from exc
        # A second read catches edits made while the page was being assembled.
        if _revision(path.read_bytes()) != revision:
            raise HTTPException(status_code=409, detail="Project changed while opening the editor.")
        return HTMLResponse(html, headers={"Cache-Control": "no-store"})

    @app.put("/api/projects/{project_id}")
    def save_project(
        project_id: str,
        project: FloorplanProject,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> dict[str, object]:
        path = project_path(project_id)
        if if_match is None:
            raise HTTPException(status_code=428, detail="If-Match revision header is required.")
        image_path(project, path)
        payload = (
            json.dumps(
                project.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        with save_lock:
            current = path.read_bytes()
            if _revision(current) != if_match:
                raise HTTPException(
                    status_code=409,
                    detail="Project changed since it was opened. Reload before saving.",
                )
            temporary_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    prefix=f".{path.name}.",
                    suffix=".tmp",
                    dir=root,
                    delete=False,
                ) as temporary:
                    temporary.write(payload)
                    temporary.flush()
                    os.fsync(temporary.fileno())
                    temporary_path = Path(temporary.name)
                os.replace(temporary_path, path)
            finally:
                if temporary_path is not None and temporary_path.exists():
                    temporary_path.unlink()
        return {"saved": True, "revision": _revision(payload)}

    return app
