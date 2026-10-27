import asyncio
import base64
import hashlib
import json
from pathlib import Path

import httpx

from electrical_floorplan_engine.server import create_app


class _ASGIClient:
    """Small synchronous adapter around HTTPX's non-deprecated ASGI transport."""

    def __init__(self, app: object) -> None:
        self._app = app

    def get(self, path: str, **kwargs: object) -> httpx.Response:
        return self._request("GET", path, **kwargs)

    def put(self, path: str, **kwargs: object) -> httpx.Response:
        return self._request("PUT", path, **kwargs)

    def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        async def send() -> httpx.Response:
            transport = httpx.ASGITransport(app=self._app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                return await client.request(method, path, **kwargs)

        return asyncio.run(send())


_ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/aXcAAAAASUVORK5CYII="
)


def _workspace(tmp_path: Path, *, image_name: str = "plan.png") -> tuple[Path, Path]:
    image_path = tmp_path / image_name
    image_path.write_bytes(_ONE_PIXEL_PNG)
    project_path = tmp_path / "plan.json"
    project_path.write_text(
        json.dumps(
            {
                "title": "Rzut backendowy",
                "source_image": image_name,
                "image_mm_per_pixel": 1.0,
                "image_origin_pixel_x": 0.0,
                "image_origin_pixel_y": 0.0,
                "walls": [
                    {
                        "id": "wall-1",
                        "start": {"x": 0, "y": 0},
                        "end": {"x": 2000, "y": 0},
                        "thickness_mm": 120,
                        "role": "interior",
                    }
                ],
                "openings": [],
                "rooms": [],
                "symbols": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return project_path, image_path


def test_backend_lists_projects_serves_editor_and_raster(tmp_path: Path) -> None:
    _, image_path = _workspace(tmp_path)
    client = _ASGIClient(create_app(tmp_path))

    index = client.get("/")
    projects = client.get("/api/projects")
    editor = client.get("/editor/plan")
    image = client.get("/api/projects/plan/image")

    assert index.status_code == 200
    assert "Wybierz skalibrowany projekt" in index.text
    assert projects.status_code == 200
    assert projects.json()[0]["id"] == "plan"
    assert projects.json()[0]["editable"] is True
    assert editor.status_code == 200
    assert 'const BACKEND_PROJECT_ID = "plan";' in editor.text
    assert 'const EMBEDDED_IMAGE = "/api/projects/plan/image";' in editor.text
    assert "Waliduj i zapisz na backendzie" in editor.text
    assert "data:image/png;base64," not in editor.text
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.content == image_path.read_bytes()


def test_backend_saves_validated_project_with_revision_guard(tmp_path: Path) -> None:
    project_path, _ = _workspace(tmp_path)
    client = TestClient(create_app(tmp_path))
    opened = client.get("/api/projects/plan").json()
    original_revision = opened["revision"]
    project = opened["project"]
    project["title"] = "Rzut zapisany"
    project["walls"][0]["thickness_mm"] = 150

    response = client.put(
        "/api/projects/plan",
        headers={"If-Match": original_revision},
        json=project,
    )

    assert response.status_code == 200
    saved_revision = response.json()["revision"]
    assert saved_revision == hashlib.sha256(project_path.read_bytes()).hexdigest()
    saved = json.loads(project_path.read_text(encoding="utf-8"))
    assert saved["title"] == "Rzut zapisany"
    assert saved["walls"][0]["thickness_mm"] == 150

    project["title"] = "Próba nadpisania"
    stale = client.put(
        "/api/projects/plan",
        headers={"If-Match": original_revision},
        json=project,
    )
    assert stale.status_code == 409
    assert json.loads(project_path.read_text(encoding="utf-8"))["title"] == "Rzut zapisany"


def test_backend_requires_revision_and_rejects_invalid_geometry(tmp_path: Path) -> None:
    _workspace(tmp_path)
    client = TestClient(create_app(tmp_path))
    project = client.get("/api/projects/plan").json()["project"]

    missing_revision = client.put("/api/projects/plan", json=project)
    assert missing_revision.status_code == 428

    project["image_mm_per_pixel"] = -1
    invalid = client.put(
        "/api/projects/plan",
        headers={"If-Match": client.get("/api/projects/plan").json()["revision"]},
        json=project,
    )
    assert invalid.status_code == 422


def test_backend_rejects_image_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside_image = tmp_path / "private.png"
    outside_image.write_bytes(_ONE_PIXEL_PNG)
    project_path = workspace / "plan.json"
    project_path.write_text(
        json.dumps(
            {
                "title": "Zewnętrzny podkład",
                "source_image": str(outside_image),
                "image_mm_per_pixel": 1.0,
            }
        ),
        encoding="utf-8",
    )
    client = _ASGIClient(create_app(workspace))

    assert client.get("/editor/plan").status_code == 403
    assert client.get("/api/projects/plan/image").status_code == 403
    assert client.get("/api/projects").json()[0]["editable"] is False


def test_backend_rejects_missing_revision_and_unknown_projects(tmp_path: Path) -> None:
    _workspace(tmp_path)
    client = TestClient(create_app(tmp_path))

    assert client.get("/api/projects/does-not-exist").status_code == 404
    assert client.get("/editor/../outside").status_code in {404, 422}
