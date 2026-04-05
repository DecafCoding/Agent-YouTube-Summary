"""Rollup viewer routes — lists and displays daily markdown rollup files."""

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from agent_youtube_summary.app import _base_context, templates
from agent_youtube_summary.config import ROLLUP_OUTPUT_DIR

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def home() -> RedirectResponse:
    """Redirect home to the rollups list."""
    return RedirectResponse(url="/rollups", status_code=302)


@router.get("/rollups")
async def rollups_list(request: Request) -> HTMLResponse:
    """List all rollup markdown files, newest first."""
    rollup_dir = Path(ROLLUP_OUTPUT_DIR)
    rollup_files: list[dict] = []

    if rollup_dir.exists():
        for md_file in sorted(rollup_dir.glob("*.md"), reverse=True):
            rollup_files.append(
                {
                    "date": md_file.stem,
                    "filename": md_file.name,
                }
            )

    context = _base_context(request)
    context["rollups"] = rollup_files
    return templates.TemplateResponse(request, "rollups.html", context)


@router.get("/rollups/{date}")
async def rollup_detail(request: Request, date: str) -> HTMLResponse:
    """Display a single rollup file."""
    rollup_path = Path(ROLLUP_OUTPUT_DIR) / f"{date}.md"

    if not rollup_path.exists():
        context = _base_context(request)
        context["date"] = date
        context["content"] = None
        return templates.TemplateResponse(
            request, "rollup_detail.html", context, status_code=404
        )

    content = rollup_path.read_text(encoding="utf-8")

    context = _base_context(request)
    context["date"] = date
    context["content"] = content
    return templates.TemplateResponse(request, "rollup_detail.html", context)
