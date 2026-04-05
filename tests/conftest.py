"""
Shared test fixtures for agent-youtube-summary.

Provides sample settings, database setup helpers, and mock data used
across multiple test modules.
"""

import json

import pytest

from agent_youtube_summary.settings import ChannelConfig, SummarySettings


@pytest.fixture()
def sample_channels() -> list[ChannelConfig]:
    """Two sample channels for testing."""
    return [
        ChannelConfig(channel_id="UCYO_jab_esuFRV4b17AJtAw", name="3Blue1Brown"),
        ChannelConfig(channel_id="UCsBjURrPoezykLs9EqgamOA", name="Fireship"),
    ]


@pytest.fixture()
def sample_settings(sample_channels: list[ChannelConfig]) -> SummarySettings:
    """Default SummarySettings with two sample channels."""
    return SummarySettings(channels=sample_channels)


@pytest.fixture()
def sample_settings_json(sample_settings: SummarySettings) -> str:
    """Serialized settings JSON matching sample_settings fixture."""
    return json.dumps(
        {
            "channels": [
                {"channelId": ch.channel_id, "name": ch.name}
                for ch in sample_settings.channels
            ],
            "schedule": sample_settings.schedule,
            "channelCooldownDays": sample_settings.channel_cooldown_days,
            "maxVideosPerChannel": sample_settings.max_videos_per_channel,
            "maxTranscriptDurationMinutes": (
                sample_settings.max_transcript_duration_minutes
            ),
            "summaryModel": sample_settings.summary_model,
        }
    )


@pytest.fixture()
def sample_video_row() -> dict:
    """A sample video row as returned from the items table."""
    return {
        "video_id": "abc123def45",
        "channel_id": "UCxxxxxx",
        "channel_name": "Test Channel",
        "title": "Test Video Title",
        "description": "A description of the test video.",
        "published_at": "2025-01-15T10:30:00+00:00",
        "duration": "PT12M30S",
        "view_count": 1500000,
        "like_count": 50000,
        "comment_count": 3200,
        "thumbnail_url": "https://i.ytimg.com/vi/abc/hqdefault.jpg",
        "transcript": "Hello and welcome to the video. Today we discuss Python.",
        "status": "collected",
    }


@pytest.fixture()
def sample_summary_response() -> dict:
    """A sample parsed LLM summary response."""
    return {
        "summary": "This video covers Python basics and advanced topics.",
        "topics": ["Python", "programming", "tutorial"],
        "key_points": [
            "Python is versatile",
            "Type hints improve code quality",
            "Async patterns enable concurrency",
        ],
    }
