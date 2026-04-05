"""
Tests for the rollup generator.

Uses in-memory DB with pre-inserted test data. Covers correct markdown
structure, no-summaries handling, output directory creation, and
formatting of duration and view counts.
"""

from unittest.mock import AsyncMock, patch

import aiosqlite
import pytest

from agent_youtube_summary.db import ensure_tables, insert_summary, upsert_video
from agent_youtube_summary.rollup import (
    _format_duration,
    _format_views,
    _render_rollup,
    run_rollup,
)


@pytest.fixture()
async def mock_db():
    """Provide an in-memory database with tables created."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await ensure_tables(conn)
    yield conn
    await conn.close()


async def _insert_summarized_video(
    conn: aiosqlite.Connection,
    video_id: str = "vid1",
    channel_name: str = "Test Channel",
) -> None:
    """Insert a video and its summary into the test database."""
    await upsert_video(
        conn,
        video_id=video_id,
        channel_id="ch1",
        channel_name=channel_name,
        title=f"Video {video_id}",
        description="A test video",
        published_at="2025-01-15T10:30:00",
        duration="PT18M30S",
        view_count=124302,
        like_count=5000,
        comment_count=200,
        thumbnail_url=f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        transcript="Full transcript text here",
        status="summarized",
    )
    await insert_summary(
        conn,
        video_id=video_id,
        summary="This video covers important topics.",
        topics=["topic1", "topic2"],
        key_points=["Point A", "Point B", "Point C"],
        model_used="gpt-4o-mini",
        prompt_version="v1",
    )


class TestFormatDuration:
    """Tests for duration formatting."""

    def test_formats_minutes(self):
        assert _format_duration("PT18M30S") == "18 min"

    def test_formats_hours(self):
        assert _format_duration("PT1H30M") == "90 min"

    def test_handles_none(self):
        assert _format_duration(None) == "unknown"

    def test_handles_short_duration(self):
        assert _format_duration("PT30S") == "30 sec"


class TestFormatViews:
    """Tests for view count formatting."""

    def test_formats_with_commas(self):
        assert _format_views(124302) == "124,302 views"

    def test_handles_none(self):
        assert _format_views(None) == "unknown views"

    def test_formats_small_number(self):
        assert _format_views(42) == "42 views"


class TestRenderRollup:
    """Tests for markdown rollup rendering."""

    def test_renders_correct_structure(self):
        """Rollup has correct headings, topics, key points, and links."""
        summaries = [
            {
                "video_id": "vid1",
                "channel_name": "Test Channel",
                "title": "Test Video",
                "thumbnail_url": "https://img.example.com/thumb.jpg",
                "topics": ["Python", "async"],
                "key_points": ["Point 1", "Point 2"],
                "summary": "A great video about async Python.",
                "duration": "PT18M30S",
                "view_count": 124302,
            }
        ]
        md = _render_rollup(summaries)

        assert "# YouTube Summary" in md
        assert "## Test Channel" in md
        assert "### Test Video" in md
        assert "![thumbnail](https://img.example.com/thumb.jpg)" in md
        assert "**Topics:** Python, async" in md
        assert "- **Key Points:**" in md
        assert "  - Point 1" in md
        assert "  - Point 2" in md
        assert "**Summary:** A great video about async Python." in md
        assert "[Watch](https://youtube.com/watch?v=vid1)" in md
        assert "18 min" in md
        assert "124,302 views" in md

    def test_groups_by_channel(self):
        """Videos are grouped under their channel heading."""
        summaries = [
            {
                "video_id": "v1",
                "channel_name": "Channel A",
                "title": "Video 1",
                "topics": [],
                "key_points": [],
                "summary": "Summary 1",
                "duration": "PT5M",
                "view_count": 100,
            },
            {
                "video_id": "v2",
                "channel_name": "Channel B",
                "title": "Video 2",
                "topics": [],
                "key_points": [],
                "summary": "Summary 2",
                "duration": "PT10M",
                "view_count": 200,
            },
        ]
        md = _render_rollup(summaries)
        assert "## Channel A" in md
        assert "## Channel B" in md
        assert "---" in md

    def test_handles_missing_optional_fields(self):
        """Rollup renders without crashing when optional fields are missing."""
        summaries = [
            {
                "video_id": "v1",
                "channel_name": None,
                "title": "Video",
                "thumbnail_url": None,
                "topics": [],
                "key_points": [],
                "summary": "A summary.",
                "duration": None,
                "view_count": None,
            }
        ]
        md = _render_rollup(summaries)
        assert "## Unknown Channel" in md
        assert "unknown" in md
        assert "unknown views" in md
        assert "![thumbnail]" not in md


class TestRunRollup:
    """Tests for the full run_rollup function."""

    async def test_generates_rollup_file(self, mock_db, tmp_path):
        """Rollup file is written to the output directory."""
        await _insert_summarized_video(mock_db)

        with (
            patch(
                "agent_youtube_summary.rollup.get_connection",
                return_value=mock_db,
            ),
            patch(
                "agent_youtube_summary.rollup.ROLLUP_OUTPUT_DIR",
                str(tmp_path),
            ),
        ):
            mock_db.close = AsyncMock()
            result = await run_rollup()

        assert result is not None
        assert result.endswith(".md")
        content = (tmp_path / result.split("\\")[-1]).read_text()
        assert "# YouTube Summary" in content

    async def test_returns_none_when_no_summaries(self, mock_db):
        """Returns None when there are no summaries for today."""
        with patch(
            "agent_youtube_summary.rollup.get_connection",
            return_value=mock_db,
        ):
            mock_db.close = AsyncMock()
            result = await run_rollup()

        assert result is None
