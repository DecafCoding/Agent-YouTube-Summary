"""
Stage 1 — Collection pipeline.

Selects the next eligible channel, fetches recent videos and their
transcripts via utils-youtube, and stores everything in SQLite. Each
pipeline invocation processes exactly one channel.
"""

import logging

from utils_youtube import (
    duration_seconds,
    fetch_recent_video_ids,
    fetch_transcripts,
    fetch_video_details,
)

from agent_youtube_summary.db import (
    ensure_tables,
    get_connection,
    get_next_channel,
    sync_channels,
    update_channel_checked,
    upsert_video,
    video_exists_with_transcript,
)
from agent_youtube_summary.settings import SummarySettings

logger = logging.getLogger(__name__)


async def run_collect(settings: SummarySettings) -> int:
    """Run the full Stage 1 collection pipeline.

    Returns the count of videos upserted into the database.
    """
    if not settings.channels:
        logger.warning("No channels configured — skipping collection")
        return 0

    conn = await get_connection()
    try:
        await ensure_tables(conn)
        await sync_channels(conn, settings.channels)

        channel_id = await get_next_channel(
            conn, settings.channels, settings.channel_cooldown_days
        )
        if channel_id is None:
            logger.info("No eligible channel to check — all within cooldown")
            return 0

        channel_name = next(
            (ch.name for ch in settings.channels if ch.channel_id == channel_id),
            channel_id,
        )
        logger.info("Collecting videos for channel: %s (%s)", channel_name, channel_id)

        video_ids = await fetch_recent_video_ids(
            channel_id, max_results=settings.max_videos_per_channel
        )
        if not video_ids:
            logger.info("No recent videos found for channel %s", channel_id)
            await update_channel_checked(conn, channel_id)
            return 0

        videos = await fetch_video_details(video_ids)
        if not videos:
            logger.info("No video details returned for channel %s", channel_id)
            await update_channel_checked(conn, channel_id)
            return 0

        max_duration_seconds = settings.max_transcript_duration_minutes * 60
        need_transcript_ids: list[str] = []

        for video in videos:
            if await video_exists_with_transcript(conn, video.video_id):
                continue
            dur = duration_seconds(video.duration)
            if dur > 0 and dur > max_duration_seconds:
                logger.debug(
                    "Skipping transcript for %s — duration %ds exceeds limit %ds",
                    video.video_id,
                    dur,
                    max_duration_seconds,
                )
                continue
            need_transcript_ids.append(video.video_id)

        transcripts: dict[str, str] = {}
        if need_transcript_ids:
            transcripts = await fetch_transcripts(need_transcript_ids)

        upserted = 0
        for video in videos:
            transcript = transcripts.get(video.video_id)
            status = "collected" if transcript else "skipped"

            published_at_str = (
                video.published_at.isoformat() if video.published_at else None
            )

            await upsert_video(
                conn,
                video_id=video.video_id,
                channel_id=video.channel_id,
                channel_name=video.channel_name,
                title=video.title,
                description=video.description,
                published_at=published_at_str,
                duration=video.duration,
                view_count=video.view_count,
                like_count=video.like_count,
                comment_count=video.comment_count,
                thumbnail_url=video.thumbnail_url,
                transcript=transcript,
                status=status,
            )
            upserted += 1

        await update_channel_checked(conn, channel_id)
        logger.info(
            "Collected %d videos for channel %s (%d with transcripts)",
            upserted,
            channel_name,
            len(transcripts),
        )
        return upserted
    finally:
        await conn.close()
