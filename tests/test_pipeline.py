"""
Tests for the pipeline orchestrator.

Integration test mocking all three stages. Verifies stages run in order
and that a stage failure does not block subsequent stages.
"""

from unittest.mock import AsyncMock, patch

from agent_youtube_summary.pipeline import run_pipeline
from agent_youtube_summary.settings import SummarySettings


def _default_settings() -> SummarySettings:
    """Create default settings for pipeline tests."""
    return SummarySettings()


class TestRunPipeline:
    """Tests for the run_pipeline orchestrator."""

    async def test_all_stages_run_in_order(self):
        """All three stages execute sequentially."""
        call_order: list[str] = []

        async def mock_collect(settings):
            call_order.append("collect")
            return 3

        async def mock_summarize(settings):
            call_order.append("summarize")
            return 2

        async def mock_rollup():
            call_order.append("rollup")
            return "/data/2025-01-15.md"

        with (
            patch(
                "agent_youtube_summary.pipeline.load_settings",
                new_callable=AsyncMock,
                return_value=_default_settings(),
            ),
            patch(
                "agent_youtube_summary.pipeline.run_collect",
                side_effect=mock_collect,
            ),
            patch(
                "agent_youtube_summary.pipeline.run_summarize",
                side_effect=mock_summarize,
            ),
            patch(
                "agent_youtube_summary.pipeline.run_rollup",
                side_effect=mock_rollup,
            ),
        ):
            await run_pipeline()

        assert call_order == ["collect", "summarize", "rollup"]

    async def test_collect_failure_does_not_block_summarize(self):
        """If Stage 1 fails, Stage 2 and rollup still run."""
        call_order: list[str] = []

        async def mock_collect(settings):
            raise RuntimeError("collect failed")

        async def mock_summarize(settings):
            call_order.append("summarize")
            return 0

        async def mock_rollup():
            call_order.append("rollup")
            return None

        with (
            patch(
                "agent_youtube_summary.pipeline.load_settings",
                new_callable=AsyncMock,
                return_value=_default_settings(),
            ),
            patch(
                "agent_youtube_summary.pipeline.run_collect",
                side_effect=mock_collect,
            ),
            patch(
                "agent_youtube_summary.pipeline.run_summarize",
                side_effect=mock_summarize,
            ),
            patch(
                "agent_youtube_summary.pipeline.run_rollup",
                side_effect=mock_rollup,
            ),
        ):
            await run_pipeline()

        assert "summarize" in call_order
        assert "rollup" in call_order

    async def test_summarize_failure_does_not_block_rollup(self):
        """If Stage 2 fails, rollup still runs."""
        call_order: list[str] = []

        async def mock_collect(settings):
            call_order.append("collect")
            return 0

        async def mock_summarize(settings):
            raise RuntimeError("summarize failed")

        async def mock_rollup():
            call_order.append("rollup")
            return None

        with (
            patch(
                "agent_youtube_summary.pipeline.load_settings",
                new_callable=AsyncMock,
                return_value=_default_settings(),
            ),
            patch(
                "agent_youtube_summary.pipeline.run_collect",
                side_effect=mock_collect,
            ),
            patch(
                "agent_youtube_summary.pipeline.run_summarize",
                side_effect=mock_summarize,
            ),
            patch(
                "agent_youtube_summary.pipeline.run_rollup",
                side_effect=mock_rollup,
            ),
        ):
            await run_pipeline()

        assert "collect" in call_order
        assert "rollup" in call_order
