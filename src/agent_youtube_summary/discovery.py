"""Re-exports workspace discovery from the shared ArtimesOne utilities package."""

from utils_artimesone.discovery import DASHBOARD_ENTRY, discover_agents

__all__ = ["DASHBOARD_ENTRY", "discover_agents"]
