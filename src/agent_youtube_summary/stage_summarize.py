"""
Stage 2 — Summarization pipeline.

Reads collected videos from the database, sends each transcript to an
LLM for structured summarization, and stores the results. Uses the
OpenAI async client with JSON mode for reliable structured output.
"""

import json
import logging
from pathlib import Path

import openai

from agent_youtube_summary.config import OPENAI_API_KEY, PROMPTS_DIR
from agent_youtube_summary.db import (
    get_collected_items,
    get_connection,
    insert_summary,
    update_item_status,
)
from agent_youtube_summary.settings import SummarySettings

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1"
"""Tracks which prompt version produced each summary."""

_MAX_TRANSCRIPT_CHARS = 100_000
"""Truncation limit for transcript before sending to the LLM."""

_prompt_template_cache: str | None = None


async def _load_prompt_template() -> str:
    """Read the prompt template from disk, caching after first load."""
    global _prompt_template_cache  # noqa: PLW0603
    if _prompt_template_cache is not None:
        return _prompt_template_cache

    path = Path(PROMPTS_DIR) / "summarize_video.md"
    _prompt_template_cache = path.read_text(encoding="utf-8")
    return _prompt_template_cache


def _render_prompt(
    template: str,
    title: str,
    channel_name: str,
    description: str,
    transcript: str,
) -> str:
    """Render the prompt template with video data, truncating the transcript."""
    truncated = transcript[:_MAX_TRANSCRIPT_CHARS]
    return (
        template.replace("{{title}}", title)
        .replace("{{channel_name}}", channel_name)
        .replace("{{description}}", description or "")
        .replace("{{transcript}}", truncated)
    )


async def _call_llm(prompt: str, model: str) -> dict | None:
    """Call the OpenAI chat completions API and parse the JSON response."""
    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    try:
        response = await client.chat.completions.create(
            model=model,
            max_tokens=1024,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that summarizes YouTube "
                        "videos. Always respond with valid JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
    except openai.APITimeoutError:
        logger.error("LLM request timed out")
        return None
    except openai.RateLimitError:
        logger.error("LLM rate limit exceeded")
        return None

    raw = response.choices[0].message.content
    if not raw:
        logger.error("LLM returned empty response")
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("LLM returned invalid JSON: %s", raw[:200])
        return None

    if not isinstance(data.get("summary"), str):
        logger.error("LLM response missing 'summary' field")
        return None

    return {
        "summary": data["summary"],
        "topics": data.get("topics", []),
        "key_points": data.get("key_points", []),
    }


async def run_summarize(settings: SummarySettings) -> int:
    """Run the full Stage 2 summarization pipeline.

    Returns the count of videos successfully summarized.
    """
    conn = await get_connection()
    try:
        template = await _load_prompt_template()
        items = await get_collected_items(conn)

        if not items:
            logger.info("No collected items to summarize")
            return 0

        summarized_count = 0
        for item in items:
            prompt = _render_prompt(
                template,
                title=item["title"],
                channel_name=item["channel_name"] or "",
                description=item["description"] or "",
                transcript=item["transcript"],
            )

            result = await _call_llm(prompt, settings.summary_model)
            if result is None:
                logger.warning("Summarization failed for video %s", item["video_id"])
                await update_item_status(conn, item["video_id"], "failed")
                continue

            await insert_summary(
                conn,
                video_id=item["video_id"],
                summary=result["summary"],
                topics=result["topics"],
                key_points=result["key_points"],
                model_used=settings.summary_model,
                prompt_version=PROMPT_VERSION,
            )
            await update_item_status(conn, item["video_id"], "summarized")
            summarized_count += 1
            logger.info("Summarized video %s", item["video_id"])

        return summarized_count
    finally:
        await conn.close()
