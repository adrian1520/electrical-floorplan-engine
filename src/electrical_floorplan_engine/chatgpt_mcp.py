"""MCP Apps adapter that renders the geometry editor inside compatible chat clients."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import mimetypes
import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Any

import mcp.types as types
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import ValidationError
from starlette.types import ASGIApp, Receive, Scope, Send

from electrical_floorplan_engine.geometry import validate_geometry
from electrical_floorplan_engine.models import FloorplanProject

RESOURCE_URI = "ui://electrical-floorplan/geometry-editor-v1.html"
RESOURCE_MIME_TYPE = "text/html;profile=mcp-app"
_PROJECT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_MAX_IMAGE_BYTES = 12 * 1024 * 1024
WORKSPACE = Path(os.getenv("ELECTRICAL_FLOORPLAN_WORKSPACE", "workspace")).expanduser().resolve()
_SAVE_LOCK = threading.Lock()
_WIDGET_PATH = Path(__file__).with_name("mcp_floorplan_widget.html")


def _transport_security_settings() -> TransportSecuritySettings:
    """Allow deployment hosts to opt into MCP's DNS-rebinding protections."""
    allowed_hosts = _split_env_list(os.getenv("MCP_ALLOWED_HOSTS"))
    allowed_origins = _split_env_list(os.getenv("MCP_ALLOWED_ORIGINS"))
    if allowed_hosts or allowed_origins:
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts,
            allowed_origins=allowed_origins,
        )
    return TransportSecuritySettings(enable_dns_rebinding_protection=False)


def _split_env_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


mcp = FastMCP(
    name="Electrical Floorplan Editor",
    instructions=(
        "Open the floorplan geometry editor to visually inspect and edit calibrated projects. "
        "Do not claim project changes were saved unless save_floorplan_project succeeds."
    ),
    stateless_http=True,
    transport_security=_transport_security_settings(),
)


class ToolFailure(ValueError):
    """An actionable error intended to be shown in the editor or conversation."""


def _project_path(project_id: str) -> Path:
    """Resolve a JSON project identifier inside the configured workspace."""
    if not _PROJECT_ID.fullmatch(project_id) or ".." in project_id:
        raise ToolFailure("Nieprawidłowy identyfikator projektu.")
    path = (WORKSPACE / f"{project_id}.json").resolve()
    if path.parent != WORKSPACE or not path.is_file():
        raise ToolFailure("Nie znaleziono projektu w katalogu roboczym backendu.")
    return path


def _revision(content: bytes) -> str:
    """Return the SHA-256 hash of the exact persisted project bytes."""
    return hashlib.sha256(content).hexdigest()


def _project_and_revision(path: Path) -> tuple[FloorplanProject, bytes, str]:
    """Read and validate one project file."""
    try:
        content = path.read_bytes()
        raw = json.loads(content)
        project = FloorplanProject.model_validate(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise ToolFailure("Projekt JSON jest nieprawidłowy lub niezgodny z modelem.") from exc
    return project, content, _revision(content)


def _image_path(project: FloorplanProject, project_file: Path) -> tuple[Path, str]:
    """Require a supported raster under the workspace before returning it."""
    if not project.source_image or project.image_mm_per_pixel is None:
        raise ToolFailure("Projekt wymaga pól source_image oraz image_mm_per_pixel (kalibracja).")
    source = Path(project.source_image)
    if not source.is_absolute():
        source = project_file.parent / source
    try:
        source = source.resolve(strict=True)
    except OSError as exc:
        raise ToolFailure("Nie znaleziono obrazu źródłowego.") from exc
    if not source.is_relative_to(WORKSPACE) or not source.is_file():
        raise ToolFailure("Obraz źródłowy musi znajdować się w katalogu workspace.")
    mime_type, _ = mimetypes.guess_type(source.name)
    if not mime_type or not mime_type.startswith("image/") or mime_type == "image/svg+xml":
        raise ToolFailure("Obsługiwane są rastrowe obrazy źródłowe, nie pliki SVG.")
    if source.stat().st_size > _MAX_IMAGE_BYTES:
        raise ToolFailure(
            "Obraz przekracza limit 12 MiB dla widżetu w rozmowie. "
            "Zmniejsz jego rozmiar i spróbuj ponownie."
        )
    return source, mime_type


def _list_projects() -> list[dict[str, Any]]:
    """Return projects that are eligible for inline editing."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    for path in sorted(WORKSPACE.glob("*.json"), key=lambda item: item.name.casefold()):
        project_id = path.stem
        if not _PROJECT_ID.fullmatch(project_id) or ".." in project_id:
            continue
        entry: dict[str, Any] = {
            "id": project_id,
            "title": project_id,
            "editable": False,
            "reason": "Projekt nie jest gotowy do edycji.",
        }
        try:
            project, _, revision = _project_and_revision(path)
            _image_path(project, path)
            entry.update(
                {
                    "title": project.title,
                    "editable": True,
                    "reason": None,
                    "revision": revision,
                }
            )
        except (OSError, ValueError) as exc:
            entry["reason"] = str(exc)
        entries.append(entry)
    return entries


def _load_project(project_id: str) -> dict[str, Any]:
    """Load a calibrated project and its raster as a widget-ready data URI."""
    path = _project_path(project_id)
    project, _, revision = _project_and_revision(path)
    image, mime_type = _image_path(project, path)
    payload = base64.b64encode(image.read_bytes()).decode("ascii")
    return {
        "id": project_id,
        "revision": revision,
        "project": project.model_dump(mode="json"),
        "image_name": image.name,
        "image_data_url": f"data:{mime_type};base64,{payload}",
    }


def _save_project(project_id: str, revision: str, project_json: str) -> dict[str, Any]:
    """Validate and atomically save a project if its revision has not changed."""
    path = _project_path(project_id)
    try:
        raw = json.loads(project_json)
        project = FloorplanProject.model_validate(raw)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise ToolFailure(
            "Nie można zapisać projektu: JSON lub geometria są nieprawidłowe."
        ) from exc
    _image_path(project, path)
    payload = (
        json.dumps(
            project.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    with _SAVE_LOCK:
        if _revision(path.read_bytes()) != revision:
            raise ToolFailure(
                "Konflikt zapisu (HTTP 409): projekt zmienił się od czasu otwarcia. "
                "Wczytaj ponownie aktualną wersję przed kolejnym zapisem."
            )
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{path.name}.",
                suffix=".tmp",
                dir=WORKSPACE,
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
    return {"saved": True, "revision": _revision(payload), "project_id": project_id}


def _validate_project(project_json: str) -> dict[str, Any]:
    """Validate model invariants and return deterministic geometry diagnostics."""
    try:
        project = FloorplanProject.model_validate_json(project_json)
    except (ValidationError, ValueError) as exc:
        raise ToolFailure("Model JSON jest nieprawidłowy: " + str(exc)) from exc
    issues = [issue.to_dict() for issue in validate_geometry(project)]
    return {"valid": True, "issues": issues, "project": project.model_dump(mode="json")}


def _widget_meta() -> dict[str, Any]:
    """Expose the UI resource to tools invoked from inside the widget."""
    return {
        "ui": {"resourceUri": RESOURCE_URI},
        "openai/widgetAccessible": True,
    }


def _tool_meta() -> dict[str, Any]:
    """Attach the UI resource and invocation labels to the widget-launch tool."""
    return {
        **_widget_meta(),
        "openai/toolInvocation/invoking": "Otwieranie edytora rzutu…",
        "openai/toolInvocation/invoked": "Edytor rzutu gotowy",
    }


def _tool_specs() -> list[types.Tool]:
    """Declare MCP tools and attach the inline UI to the editor launch tool."""
    no_args = {"type": "object", "properties": {}, "additionalProperties": False}
    project_id_schema = {
        "type": "object",
        "properties": {"project_id": {"type": "string", "minLength": 1}},
        "required": ["project_id"],
        "additionalProperties": False,
    }
    return [
        types.Tool(
            name="open_floorplan_editor",
            title="Otwórz edytor geometrii rzutu",
            description=(
                "Otwiera interaktywny edytor geometrii bezpośrednio w rozmowie. "
                "Użytkownik może wybrać skalibrowany projekt, edytować ściany, pomieszczenia "
                "i otwory, a następnie zapisać zmiany w backendzie."
            ),
            inputSchema=no_args,
            _meta=_tool_meta(),
            annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
        ),
        types.Tool(
            name="list_floorplan_projects",
            title="Lista projektów rzutów",
            description="Listuje projekty JSON dostępne w katalogu workspace backendu.",
            inputSchema=no_args,
            _meta=_widget_meta(),
            annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
        ),
        types.Tool(
            name="load_floorplan_project",
            title="Wczytaj projekt rzutu",
            description="Wczytuje projekt, jego rewizję i skalibrowany raster do edytora.",
            inputSchema=project_id_schema,
            _meta=_widget_meta(),
            annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
        ),
        types.Tool(
            name="save_floorplan_project",
            title="Zapisz geometrię rzutu",
            description=(
                "Waliduje i atomowo zapisuje projekt tylko wtedy, gdy przesłana rewizja "
                "SHA-256 nadal odpowiada plikowi w backendzie."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "minLength": 1},
                    "revision": {"type": "string", "minLength": 64, "maxLength": 64},
                    "project_json": {
                        "type": "string",
                        "description": "Kompletny JSON projektu po edycji.",
                    },
                },
                "required": ["project_id", "revision", "project_json"],
                "additionalProperties": False,
            },
            _meta=_widget_meta(),
            annotations={"readOnlyHint": False, "destructiveHint": True, "openWorldHint": False},
        ),
        types.Tool(
            name="validate_floorplan_project",
            title="Waliduj projekt rzutu",
            description="Waliduje model projektu i zwraca ostrzeżenia geometrii bez zapisu.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_json": {"type": "string", "description": "Kompletny JSON projektu."}
                },
                "required": ["project_json"],
                "additionalProperties": False,
            },
            _meta=_widget_meta(),
            annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
        ),
    ]


@mcp._mcp_server.list_tools()
async def _list_tools() -> list[types.Tool]:
    return _tool_specs()


@mcp._mcp_server.list_resources()
async def _list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            name="Edytor geometrii rzutu",
            title="Edytor geometrii rzutu",
            uri=RESOURCE_URI,
            description="Interaktywny edytor geometrii rzutu z podkładem rastrowym.",
            mimeType=RESOURCE_MIME_TYPE,
            _meta={"ui": {"prefersBorder": True}},
        )
    ]


@mcp._mcp_server.list_resource_templates()
async def _list_resource_templates() -> list[types.ResourceTemplate]:
    return [
        types.ResourceTemplate(
            name="Edytor geometrii rzutu",
            title="Edytor geometrii rzutu",
            uriTemplate=RESOURCE_URI,
            description="Interaktywny edytor geometrii rzutu z podkładem rastrowym.",
            mimeType=RESOURCE_MIME_TYPE,
            _meta={"ui": {"prefersBorder": True}},
        )
    ]


async def _read_resource(request: types.ReadResourceRequest) -> types.ServerResult:
    if str(request.params.uri) != RESOURCE_URI:
        return types.ServerResult(
            types.ReadResourceResult(
                contents=[],
                _meta={"error": "Nieznany zasób interfejsu."},
            )
        )
    try:
        html = _WIDGET_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        return types.ServerResult(types.ReadResourceResult(contents=[], _meta={"error": str(exc)}))
    return types.ServerResult(
        types.ReadResourceResult(
            contents=[
                types.TextResourceContents(
                    uri=RESOURCE_URI,
                    mimeType=RESOURCE_MIME_TYPE,
                    text=html,
                    _meta={"ui": {"prefersBorder": True}},
                )
            ]
        )
    )


def _tool_response(
    text: str,
    structured_content: dict[str, Any],
    *,
    meta: dict[str, Any] | None = None,
) -> types.ServerResult:
    return types.ServerResult(
        types.CallToolResult(
            content=[types.TextContent(type="text", text=text)],
            structuredContent=structured_content,
            _meta=meta,
        )
    )


def _tool_error(text: str) -> types.ServerResult:
    return types.ServerResult(
        types.CallToolResult(
            content=[types.TextContent(type="text", text=text)],
            isError=True,
        )
    )


async def _call_tool(request: types.CallToolRequest) -> types.ServerResult:
    arguments = request.params.arguments or {}
    try:
        if request.params.name == "open_floorplan_editor":
            projects = _list_projects()
            return _tool_response(
                (
                    "Edytor rzutu gotowy. Projekty dostępne do edycji: "
                    f"{sum(bool(item['editable']) for item in projects)}."
                ),
                {"projects": projects},
                meta={
                    "openai/toolInvocation/invoking": "Otwieranie edytora rzutu…",
                    "openai/toolInvocation/invoked": "Edytor rzutu gotowy",
                },
            )
        if request.params.name == "list_floorplan_projects":
            return _tool_response("Lista projektów workspace.", {"projects": _list_projects()})
        if request.params.name == "load_floorplan_project":
            result = _load_project(str(arguments.get("project_id", "")))
            return _tool_response(
                f"Wczytano projekt {result['project']['title']}.",
                result,
            )
        if request.params.name == "save_floorplan_project":
            result = _save_project(
                str(arguments.get("project_id", "")),
                str(arguments.get("revision", "")),
                str(arguments.get("project_json", "")),
            )
            return _tool_response("Projekt został zwalidowany i zapisany.", result)
        if request.params.name == "validate_floorplan_project":
            result = _validate_project(str(arguments.get("project_json", "")))
            return _tool_response("Walidacja projektu zakończona.", result)
        return _tool_error("Nieznane narzędzie edytora rzutu.")
    except (OSError, ValueError) as exc:
        return _tool_error(str(exc))


mcp._mcp_server.request_handlers[types.CallToolRequest] = _call_tool
mcp._mcp_server.request_handlers[types.ReadResourceRequest] = _read_resource
app = mcp.streamable_http_app()

# Write-capable endpoints are fail-closed unless a bearer token is configured.
# Configure the same API key in the ChatGPT custom-app connection.
_API_TOKEN = os.getenv("ELECTRICAL_FLOORPLAN_API_TOKEN", "")


class BearerTokenMiddleware:
    """Pure ASGI auth middleware; preserves MCP streaming responses."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path", "").rstrip("/") != "/mcp":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        provided = headers.get(b"authorization", b"").decode("latin-1")
        expected = f"Bearer {self.token}"
        if self.token and hmac.compare_digest(provided, expected):
            await self.app(scope, receive, send)
            return

        detail = (
            "MCP API token is missing or invalid."
            if self.token
            else "Set ELECTRICAL_FLOORPLAN_API_TOKEN before exposing this endpoint."
        )
        body = json.dumps({"detail": detail}).encode("utf-8")
        response_headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
            (b"www-authenticate", b"Bearer"),
        ]
        await send(
            {
                "type": "http.response.start",
                "status": 401 if self.token else 503,
                "headers": response_headers,
            }
        )
        await send({"type": "http.response.body", "body": body})


app.add_middleware(BearerTokenMiddleware, token=_API_TOKEN)
