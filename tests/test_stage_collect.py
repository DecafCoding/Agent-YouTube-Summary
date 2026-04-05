"""
Tests for Stage 1 — Collection pipeline.

Mocks all utils-youtube calls and database connection. Tests the full
happy path, no-eligible-channel early exit, duration filtering,
existing-video skip, and transcript-fetch failure.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import aiosqlite
import pytest
from utils_youtube.models import VideoMetadata

from agent_youtube_summary.db import ensure_tables, get_collected_items
from agent_youtube_summary.settings import ChannelConfig, SummarySettings
from agent_youtube_summary.stage_collect import run_collect


def _make_video(
    video_id: str,
    duration: str = "PT10M",
    channel_id: str = "UCtest",
    channel_name: str = "Test",
) -> VideoMetadata:
    """Create a VideoMetadata instance for testing."""
    return VideoMetadata(
        video_id=video_id,
        channel_id=channel_id,
        channel_name=channel_name,
        title=f"Video {video_id}",
        description="Test description",
        published_at=datetime(2025, 1, 15, 10, 30),
        duration=duration,
        view_count=1000,
        like_count=50,
        comment_count=10,
        thumbnail_url=f"https://img.youtube.com/{video_id}.jpg",
    )


@pytest.fixture()
async def mock_db():
    """Provide an in-memory database pretending to be the real connection."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await ensure_tables(conn)
    yield conn
    await conn.close()


def _settings(channels: list[ChannelConfig] | None = None) -> SummarySettings:
    """Create test settings with optional channel override."""
    if channels is None:
        channels = [ChannelConfig(channel_id="UCtest", name="Test Channel")]
    return SummarySettings(
        channels=channels,
        max_videos_per_channel=5,
        max_transcript_duration_minutes=60,
        channel_cooldown_days=3,
    )


class TestRunCollect:
    """Tests for the run_collect pipeline function."""

    async def test_happy_path_collects_videos(self, mock_db):
        """Full pipeline collects videos and stores them with transcripts."""
        videos = [_make_video("vid1"), _make_video("vid2")]
        transcripts = {"vid1": "Transcript for vid1", "vid2": "Transcript for vid2"}

        with (
            patch(
                "agent_youtube_summary.stage_collect.get_connection",
                return_value=mock_db,
            ),
            patch(
                "agent_youtube_summary.stage_collect.fetch_recent_video_ids",
                new_callable=AsyncMock,
                return_value=["vid1", "vid2"],
            ),
            patch(
                "agent_youtube_summary.stage_collect.fetch_video_details",
                new_callable=AsyncMock,
                return_value=videos,
            ),
            patch(
                "agent_youtube_summary.stage_collect.fetch_transcripts",
                new_callable=AsyncMock,
                return_value=transcripts,
            ),
        ):
            # Prevent close since we manage the fixture
            mock_db.close = AsyncMock()
            count = await run_collect(_settings())

        assert count == 2
        items = await get_collected_items(mock_db)
        assert len(items) == 2
        assert all(item["status"] == "collected" for item in items)

    async def test_no_eligible_channel_returns_zero(self, mock_db):
        """Returns 0 when no channel is due for checking."""
        with patch(
            "agent_youtube_summary.stage_collect.get_connection",
            return_value=mock_db,
        ):
            mock_db.close = AsyncMock()
            # Empty channels → no eligible channel
            count = await run_collect(_settings(channels=[]))

        assert count == 0

    async def test_duration_filtering_skips_long_videos(self, mock_db):
        """Videos exceeding duration limit are not fetched for transcripts."""
        short_video = _make_video("short", duration="PT10M")
        long_video = _make_video("long", duration="PT120M")

        with (
            patch(
                "agent_youtube_summary.stage_collect.get_connection",
                return_value=mock_db,
            ),
            patch(
                "agent_youtube_summary.stage_collect.fetch_recent_video_ids",
                new_callable=AsyncMock,
                return_value=["short", "long"],
            ),
            patch(
                "agent_youtube_summary.stage_collect.fetch_video_details",
                new_callable=AsyncMock,
                return_value=[short_video, long_video],
            ),
            patch(
                "agent_youtube_summary.stage_collect.fetch_transcripts",
                new_callable=AsyncMock,
                return_value={"short": "Transcript"},
            ) as mock_fetch_transcripts,
        ):
            mock_db.close = AsyncMock()
            count = await run_collect(_settings())

        assert count == 2
        # Only the short video should have been requested for transcripts
        mock_fetch_transcripts.assert_called_once_with(["short"])

    async def test_existing_video_with_transcript_is_skipped(self, mock_db):
        """Videos already in DB with transcript are not fetched again."""
        # Pre-insert a video with transcript
        await mock_db.execute(
            """
            INSERT INTO agent_youtube_summary_items
                (video_id, channel_id, title, transcript, status)
            VALUES ('vid1', 'UCtest', 'Existing', 'existing transcript', 'collected')
            """
        )
        await mock_db.commit()

        video = _make_video("vid1")
        with (
            patch(
                "agent_youtube_summary.stage_collect.get_connection",
                return_value=mock_db,
            ),
            patch(
                "agent_youtube_summary.stage_collect.fetch_recent_video_ids",
                new_callable=AsyncMock,
                return_value=["vid1"],
            ),
            patch(
                "agent_youtube_summary.stage_collect.fetch_video_details",
                new_callable=AsyncMock,
                return_value=[video],
            ),
            patch(
                "agent_youtube_summary.stage_collect.fetch_transcripts",
                new_callable=AsyncMock,
                return_value={},
            ) as mock_fetch_transcripts,
        ):
            mock_db.close = AsyncMock()
            await run_collect(_settings())

        # Should not request transcripts for existing video
        mock_fetch_transcripts.assert_not_called()

    async def test_missing_transcript_marks_as_skipped(self, mock_db):
        """Videos without transcripts are stored with status 'skipped'."""
        video = _make_video("vid1")
        with (
            patch(
                "agent_youtube_summary.stage_collect.get_connection",
                return_value=mock_db,
            ),
            patch(
                "agent_youtube_summary.stage_collect.fetch_recent_video_ids",
                new_callable=AsyncMock,
                return_value=["vid1"],
            ),
            patch(
                "agent_youtube_summary.stage_collect.fetch_video_details",
                new_callable=AsyncMock,
                return_value=[video],
            ),
            patch(
                "agent_youtube_summary.stage_collect.fetch_transcripts",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            mock_db.close = AsyncMock()
            count = await run_collect(_settings())

        assert count == 1
        cursor = await mock_db.execute(
            "SELECT status FROM agent_youtube_summary_items WHERE video_id = 'vid1'"
        )
        row = await cursor.fetchone()
        assert row["status"] == "skipped"

    async def test_empty_video_ids_returns_zero(self, mock_db):
        """Returns 0 when fetch_recent_video_ids returns an empty list."""
        with (
            patch(
                "agent_youtube_summary.stage_collect.get_connection",
                return_value=mock_db,
            ),
            patch(
                "agent_youtube_summary.stage_collect.fetch_recent_video_ids",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            mock_db.close = AsyncMock()
            count = await run_collect(_settings())

        assert count == 0

    async def test_empty_video_details_returns_zero(self, mock_db):
        """Returns 0 when fetch_video_details returns an empty list."""
        with (
            patch(
                "agent_youtube_summary.stage_collect.get_connection",
                return_value=mock_db,
            ),
            patch(
                "agent_youtube_summary.stage_collect.fetch_recent_video_ids",
                new_callable=AsyncMock,
                return_value=["vid1"],
            ),
            patch(
                "agent_youtube_summary.stage_collect.fetch_video_details",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            mock_db.close = AsyncMock()
            count = await run_collect(_settings())

        assert count == 0
