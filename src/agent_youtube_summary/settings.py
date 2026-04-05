"""
Settings loader for the agent-youtube-summary agent.

Loads and validates settings.json against the Pydantic model at runtime.
The JSON file uses camelCase keys (matching the JSON schema for Dashboard
rendering), while the Python model uses snake_case with Pydantic aliases.
"""

import json
import logging
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from agent_youtube_summary.config import SETTINGS_PATH

logger = logging.getLogger(__name__)


class ChannelConfig(BaseModel):
    """A single YouTube channel to monitor."""

    model_config = ConfigDict(populate_by_name=True)

    channel_id: str = Field(alias="channelId")
    name: str


class SummarySettings(BaseModel):
    """All configurable behavior for the YouTube Summary agent."""

    model_config = ConfigDict(populate_by_name=True)

    channels: list[ChannelConfig] = Field(default_factory=list)
    schedule: str = "0 */1 * * *"
    channel_cooldown_days: int = Field(default=3, alias="channelCooldownDays")
    max_videos_per_channel: int = Field(default=5, alias="maxVideosPerChannel")
    max_transcript_duration_minutes: int = Field(
        default=60, alias="maxTranscriptDurationMinutes"
    )
    summary_model: str = Field(default="gpt-4o-mini", alias="summaryModel")


async def load_settings() -> SummarySettings:
    """Load and validate settings from the settings.json file.

    Returns defaults if the file is missing or contains invalid JSON.
    """
    path = Path(SETTINGS_PATH)
    if not path.exists():
        logger.warning("Settings file not found at %s, using defaults", path)
        return SummarySettings()

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return SummarySettings.model_validate(data)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Invalid settings file at %s: %s — using defaults", path, exc)
        return SummarySettings()
