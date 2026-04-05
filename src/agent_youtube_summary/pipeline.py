"""
Pipeline orchestrator — top-level entry point.

Runs all three stages sequentially: collect, summarize, rollup.
Each stage is independent and a failure in one does not block the next.
"""

import asyncio
import logging
import time

from agent_youtube_summary.rollup import run_rollup
from agent_youtube_summary.settings import load_settings
from agent_youtube_summary.stage_collect import run_collect
from agent_youtube_summary.stage_summarize import run_summarize

logger = logging.getLogger(__name__)


async def run_pipeline() -> None:
    """Run the full collect -> summarize -> rollup pipeline."""
    start = time.monotonic()
    settings = await load_settings()

    logger.info("Starting pipeline run")

    try:
        collected = await run_collect(settings)
        logger.info("Stage 1 (collect): %d videos", collected)
    except Exception:
        logger.exception("Stage 1 (collect) failed")

    try:
        summarized = await run_summarize(settings)
        logger.info("Stage 2 (summarize): %d videos", summarized)
    except Exception:
        logger.exception("Stage 2 (summarize) failed")

    try:
        rollup_path = await run_rollup()
        if rollup_path:
            logger.info("Rollup written to %s", rollup_path)
        else:
            logger.info("No summaries to roll up today")
    except Exception:
        logger.exception("Rollup failed")

    elapsed = time.monotonic() - start
    logger.info("Pipeline completed in %.1fs", elapsed)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    asyncio.run(run_pipeline())
