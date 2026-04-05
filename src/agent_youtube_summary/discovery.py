"""
Workspace scanner for ArtimesOne agent discovery.

Scans the workspace root for Agent-*/ directories containing registry.json
files and returns a sorted list of sidebar entries. Used by the FastAPI app
to populate the sidebar on each request.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DASHBOARD_ENTRY: dict = {
    "id": "artimesone",
    "name": "Dashboard",
    "category": "Platform",
    "icon": "home",
    "url": "http://localhost:8000",
}
"""Hardcoded Dashboard sidebar entry — always appears first."""

_REQUIRED_FIELDS = {"id", "name", "category", "icon", "url"}


def discover_agents(workspace_dir: str) -> list[dict]:
    """Scan the workspace for Agent-*/registry.json files and build sidebar data.

    Returns a list of sidebar entry dicts sorted by category (Platform first,
    then Agent) and alphabetically by name within each category.
    """
    workspace = Path(workspace_dir)
    agents: list[dict] = [DASHBOARD_ENTRY.copy()]

    for candidate in workspace.glob("Agent-*"):
        if not candidate.is_dir():
            continue

        registry_path = candidate / "registry.json"
        if not registry_path.exists():
            logger.debug("No registry.json in %s — skipping", candidate.name)
            continue

        try:
            raw = registry_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Malformed registry.json in %s: %s — skipping", candidate.name, exc
            )
            continue

        if not _REQUIRED_FIELDS.issubset(data.keys()):
            missing = _REQUIRED_FIELDS - data.keys()
            logger.warning(
                "registry.json in %s missing fields %s — skipping",
                candidate.name,
                missing,
            )
            continue

        agents.append(data)

    def _sort_key(entry: dict) -> tuple[int, str]:
        category_order = 0 if entry["category"] == "Platform" else 1
        return (category_order, entry["name"])

    agents.sort(key=_sort_key)
    return agents
