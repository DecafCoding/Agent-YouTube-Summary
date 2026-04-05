"""Settings page routes — renders form from schema, reads/writes settings.json."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from agent_youtube_summary.app import _base_context, templates
from agent_youtube_summary.config import SETTINGS_PATH

logger = logging.getLogger(__name__)

router = APIRouter()

_SETTINGS_FILE = Path(SETTINGS_PATH)
_SCHEMA_FILE = _SETTINGS_FILE.parent / "settings.schema.json"


@router.get("/settings")
async def settings_page(request: Request) -> HTMLResponse:
    """Render the settings form populated with current values."""
    schema: dict = {}
    if _SCHEMA_FILE.exists():
        try:
            schema = json.loads(_SCHEMA_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load settings schema: %s", exc)

    values: dict = {}
    if _SETTINGS_FILE.exists():
        try:
            values = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load current settings: %s", exc)

    context = _base_context(request)
    context["schema"] = schema
    context["values"] = values
    return templates.TemplateResponse(request, "settings.html", context)


@router.post("/settings")
async def save_settings(request: Request) -> JSONResponse:
    """Save settings from the form submission."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"status": "error", "message": "Invalid JSON body"}, status_code=400
        )

    if not isinstance(body, dict):
        return JSONResponse(
            {"status": "error", "message": "Expected a JSON object"}, status_code=400
        )

    try:
        _SETTINGS_FILE.write_text(
            json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        logger.error("Failed to write settings: %s", exc)
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)

    logger.info("Settings saved to %s", _SETTINGS_FILE)
    return JSONResponse({"status": "ok"})
