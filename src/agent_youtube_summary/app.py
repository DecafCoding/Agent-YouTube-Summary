"""FastAPI web application for the YouTube Summary agent."""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from agent_youtube_summary.config import HOST, PORT, SHARED_DIR, WORKSPACE_DIR
from agent_youtube_summary.discovery import discover_agents

AGENT_ID = "agent-youtube-summary"
"""Identifier used for sidebar active-state highlighting."""

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

app = FastAPI(title="YouTube Summary")

app.mount(
    "/static/shared",
    StaticFiles(directory=SHARED_DIR),
    name="shared",
)

templates = Jinja2Templates(
    directory=[
        str(_PROJECT_ROOT / "templates"),
        os.path.join(SHARED_DIR, "templates"),
    ]
)


def _base_context(request: Request) -> dict:
    """Build the template context with sidebar data for every page."""
    agents = discover_agents(WORKSPACE_DIR)
    return {
        "request": request,
        "sidebar_agents": agents,
        "active_agent_id": AGENT_ID,
    }


# Router imports are at the bottom to avoid circular imports — route modules
# import templates and _base_context from this module, so those must be
# defined before the route modules are loaded.
from agent_youtube_summary.routes.rollups import router as rollups_router  # noqa: E402
from agent_youtube_summary.routes.settings_page import (  # noqa: E402
    router as settings_router,
)

app.include_router(settings_router)
app.include_router(rollups_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("agent_youtube_summary.app:app", host=HOST, port=int(PORT), reload=True)
