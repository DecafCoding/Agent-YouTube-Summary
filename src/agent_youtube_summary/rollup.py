"""
Rollup generator — deterministic markdown daily digest.

Assembles today's summaries from the database into a markdown file
grouped by channel. No LLM involved — pure template rendering.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

from utils_youtube import duration_seconds

from agent_youtube_summary.config import ROLLUP_OUTPUT_DIR
from agent_youtube_summary.db import get_connection, get_todays_summaries

logger = logging.getLogger(__name__)


def _format_duration(iso_duration: str | None) -> str:
    """Convert an ISO 8601 duration to a human-readable string like '18 min'."""
    seconds = duration_seconds(iso_duration)
    if seconds <= 0:
        return "unknown"
    minutes = seconds // 60
    if minutes < 1:
        return f"{seconds} sec"
    return f"{minutes} min"


def _format_views(view_count: int | None) -> str:
    """Format a view count with comma separators."""
    if view_count is None:
        return "unknown views"
    return f"{view_count:,} views"


def _render_rollup(summaries: list[dict]) -> str:
    """Render the markdown rollup from a list of summary-item joined rows."""
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    lines: list[str] = [f"# YouTube Summary — {today}", ""]

    current_channel: str | None = None
    for item in summaries:
        channel = item.get("channel_name") or "Unknown Channel"
        if channel != current_channel:
            if current_channel is not None:
                lines.append("---")
                lines.append("")
            lines.append(f"## {channel}")
            lines.append("")
            current_channel = channel

        title = item.get("title", "Untitled")
        lines.append(f"### {title}")

        thumbnail = item.get("thumbnail_url")
        if thumbnail:
            lines.append(f"![thumbnail]({thumbnail})")

        topics = item.get("topics", [])
        if topics:
            lines.append(f"- **Topics:** {', '.join(topics)}")

        key_points = item.get("key_points", [])
        if key_points:
            lines.append("- **Key Points:**")
            for point in key_points:
                lines.append(f"  - {point}")

        summary = item.get("summary", "")
        if summary:
            lines.append(f"- **Summary:** {summary}")

        video_id = item.get("video_id", "")
        duration_str = _format_duration(item.get("duration"))
        views_str = _format_views(item.get("view_count"))
        watch_url = f"https://youtube.com/watch?v={video_id}"
        lines.append(f"- [Watch]({watch_url}) | {duration_str} | {views_str}")
        lines.append("")

    return "\n".join(lines)


async def run_rollup() -> str | None:
    """Generate the daily rollup markdown file.

    Returns the file path of the generated rollup, or None if there are
    no summaries for today.
    """
    conn = await get_connection()
    try:
        summaries = await get_todays_summaries(conn)
        if not summaries:
            logger.info("No summaries for today — skipping rollup")
            return None

        markdown = _render_rollup(summaries)

        output_dir = Path(ROLLUP_OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.now(UTC).strftime("%Y-%m-%d")
        output_path = output_dir / f"{today}.md"
        output_path.write_text(markdown, encoding="utf-8")

        logger.info("Rollup written to %s", output_path)
        return str(output_path)
    finally:
        await conn.close()
