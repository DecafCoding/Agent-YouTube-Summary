"""
Tests for Stage 2 — Summarization pipeline.

Mocks the OpenAI client and database. Tests happy path, invalid JSON
handling, empty collected items, and prompt template loading.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
import pytest

from agent_youtube_summary.db import (
    ensure_tables,
    upsert_video,
)
from agent_youtube_summary.settings import ChannelConfig, SummarySettings
from agent_youtube_summary.stage_summarize import (
    _render_prompt,
    run_summarize,
)


@pytest.fixture()
async def mock_db():
    """Provide an in-memory database with tables and a collected video."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await ensure_tables(conn)
    yield conn
    await conn.close()


def _settings() -> SummarySettings:
    """Create test settings."""
    return SummarySettings(
        channels=[ChannelConfig(channel_id="UCtest", name="Test")],
        summary_model="gpt-4o-mini",
    )


def _mock_llm_response(content: str) -> MagicMock:
    """Build a mock OpenAI ChatCompletion response."""
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


class TestRenderPrompt:
    """Tests for prompt template rendering."""

    def test_renders_all_variables(self):
        """All template variables are replaced."""
        template = (
            "Title: {{title}} Channel: {{channel_name}} "
            "Desc: {{description}} Transcript: {{transcript}}"
        )
        result = _render_prompt(
            template, "My Video", "My Channel", "A description", "The transcript"
        )
        assert "{{" not in result
        assert "My Video" in result
        assert "My Channel" in result
        assert "A description" in result
        assert "The transcript" in result

    def test_truncates_long_transcript(self):
        """Transcripts exceeding the character limit are truncated."""
        template = "{{transcript}}"
        long_transcript = "x" * 200_000
        result = _render_prompt(template, "", "", "", long_transcript)
        assert len(result) == 100_000


class TestRunSummarize:
    """Tests for the run_summarize pipeline function."""

    async def test_happy_path_summarizes_video(self, mock_db):
        """Collected video is summarized and status updated."""
        await upsert_video(
            mock_db,
            "vid1",
            "ch1",
            "Channel",
            "Title",
            "Desc",
            None,
            "PT10M",
            1000,
            50,
            10,
            None,
            "transcript text",
            "collected",
        )

        llm_response = _mock_llm_response(
            json.dumps(
                {
                    "summary": "A great video.",
                    "topics": ["Python"],
                    "key_points": ["Point 1"],
                }
            )
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=llm_response)

        with (
            patch(
                "agent_youtube_summary.stage_summarize.get_connection",
                return_value=mock_db,
            ),
            patch(
                "agent_youtube_summary.stage_summarize._load_prompt_template",
                new_callable=AsyncMock,
                return_value=(
                    "{{title}} {{channel_name}} {{description}} {{transcript}}"
                ),
            ),
            patch(
                "agent_youtube_summary.stage_summarize.openai.AsyncOpenAI",
                return_value=mock_client,
            ),
        ):
            mock_db.close = AsyncMock()
            count = await run_summarize(_settings())

        assert count == 1
        cursor = await mock_db.execute(
            "SELECT status FROM agent_youtube_summary_items WHERE video_id = 'vid1'"
        )
        row = await cursor.fetchone()
        assert row["status"] == "summarized"

        cursor = await mock_db.execute(
            "SELECT summary FROM agent_youtube_summary_summaries"
            " WHERE video_id = 'vid1'"
        )
        row = await cursor.fetchone()
        assert row["summary"] == "A great video."

    async def test_invalid_json_marks_as_failed(self, mock_db):
        """Invalid JSON from LLM marks the video as failed."""
        await upsert_video(
            mock_db,
            "vid1",
            "ch1",
            "Channel",
            "Title",
            "Desc",
            None,
            "PT10M",
            1000,
            50,
            10,
            None,
            "transcript text",
            "collected",
        )

        llm_response = _mock_llm_response("not valid json {{{")

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=llm_response)

        with (
            patch(
                "agent_youtube_summary.stage_summarize.get_connection",
                return_value=mock_db,
            ),
            patch(
                "agent_youtube_summary.stage_summarize._load_prompt_template",
                new_callable=AsyncMock,
                return_value="{{title}} {{transcript}}",
            ),
            patch(
                "agent_youtube_summary.stage_summarize.openai.AsyncOpenAI",
                return_value=mock_client,
            ),
        ):
            mock_db.close = AsyncMock()
            count = await run_summarize(_settings())

        assert count == 0
        cursor = await mock_db.execute(
            "SELECT status FROM agent_youtube_summary_items WHERE video_id = 'vid1'"
        )
        row = await cursor.fetchone()
        assert row["status"] == "failed"

    async def test_empty_collected_items_returns_zero(self, mock_db):
        """Returns 0 when no collected items exist."""
        with (
            patch(
                "agent_youtube_summary.stage_summarize.get_connection",
                return_value=mock_db,
            ),
            patch(
                "agent_youtube_summary.stage_summarize._load_prompt_template",
                new_callable=AsyncMock,
                return_value="template",
            ),
        ):
            mock_db.close = AsyncMock()
            count = await run_summarize(_settings())

        assert count == 0

    async def test_llm_timeout_marks_as_failed(self, mock_db):
        """APITimeoutError from LLM marks the video as failed."""
        await upsert_video(
            mock_db,
            "vid1",
            "ch1",
            "Channel",
            "Title",
            "Desc",
            None,
            "PT10M",
            1000,
            50,
            10,
            None,
            "transcript text",
            "collected",
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=__import__("openai").APITimeoutError(request=None)
        )

        with (
            patch(
                "agent_youtube_summary.stage_summarize.get_connection",
                return_value=mock_db,
            ),
            patch(
                "agent_youtube_summary.stage_summarize._load_prompt_template",
                new_callable=AsyncMock,
                return_value="{{title}} {{transcript}}",
            ),
            patch(
                "agent_youtube_summary.stage_summarize.openai.AsyncOpenAI",
                return_value=mock_client,
            ),
        ):
            mock_db.close = AsyncMock()
            count = await run_summarize(_settings())

        assert count == 0
        cursor = await mock_db.execute(
            "SELECT status FROM agent_youtube_summary_items WHERE video_id = 'vid1'"
        )
        row = await cursor.fetchone()
        assert row["status"] == "failed"

    async def test_llm_rate_limit_marks_as_failed(self, mock_db):
        """RateLimitError from LLM marks the video as failed."""
        await upsert_video(
            mock_db,
            "vid1",
            "ch1",
            "Channel",
            "Title",
            "Desc",
            None,
            "PT10M",
            1000,
            50,
            10,
            None,
            "transcript text",
            "collected",
        )

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=__import__("openai").RateLimitError(
                message="rate limited",
                response=mock_response,
                body=None,
            )
        )

        with (
            patch(
                "agent_youtube_summary.stage_summarize.get_connection",
                return_value=mock_db,
            ),
            patch(
                "agent_youtube_summary.stage_summarize._load_prompt_template",
                new_callable=AsyncMock,
                return_value="{{title}} {{transcript}}",
            ),
            patch(
                "agent_youtube_summary.stage_summarize.openai.AsyncOpenAI",
                return_value=mock_client,
            ),
        ):
            mock_db.close = AsyncMock()
            count = await run_summarize(_settings())

        assert count == 0
        cursor = await mock_db.execute(
            "SELECT status FROM agent_youtube_summary_items WHERE video_id = 'vid1'"
        )
        row = await cursor.fetchone()
        assert row["status"] == "failed"
