"""
SQLite data layer for the agent-youtube-summary agent.

Manages three prefixed tables in the shared ArtimesOne database:
channels, items, and summaries. All operations are async via aiosqlite.
Callers manage the connection lifecycle — every function takes a conn parameter.
"""

import json
import logging
from datetime import UTC, datetime, timedelta

import aiosqlite

from agent_youtube_summary.config import DB_PATH
from agent_youtube_summary.settings import ChannelConfig

logger = logging.getLogger(__name__)


async def get_connection() -> aiosqlite.Connection:
    """Open a connection to the shared SQLite database with WAL mode enabled."""
    conn = await aiosqlite.connect(DB_PATH)
    await conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = aiosqlite.Row
    return conn


async def ensure_tables(conn: aiosqlite.Connection) -> None:
    """Create the three agent tables if they do not already exist."""
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_youtube_summary_channels (
            channel_id      TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            last_checked_at TIMESTAMP,
            added_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_youtube_summary_items (
            video_id        TEXT PRIMARY KEY,
            channel_id      TEXT NOT NULL,
            channel_name    TEXT,
            title           TEXT NOT NULL,
            description     TEXT,
            published_at    TIMESTAMP,
            duration        TEXT,
            view_count      INTEGER,
            like_count      INTEGER,
            comment_count   INTEGER,
            thumbnail_url   TEXT,
            transcript      TEXT,
            collected_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status          TEXT NOT NULL DEFAULT 'collected'
        )
        """
    )
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_youtube_summary_summaries (
            video_id        TEXT PRIMARY KEY,
            summary         TEXT NOT NULL,
            topics          TEXT,
            key_points      TEXT,
            model_used      TEXT,
            prompt_version  TEXT,
            summarized_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await conn.commit()


async def sync_channels(
    conn: aiosqlite.Connection,
    channels: list[ChannelConfig],
) -> None:
    """Insert channels from settings that do not already exist in the table."""
    for ch in channels:
        await conn.execute(
            """
            INSERT OR IGNORE INTO agent_youtube_summary_channels (channel_id, name)
            VALUES (?, ?)
            """,
            (ch.channel_id, ch.name),
        )
    await conn.commit()


async def get_next_channel(
    conn: aiosqlite.Connection,
    channels: list[ChannelConfig],
    cooldown_days: int,
) -> str | None:
    """Return the channel_id of the next eligible channel to check.

    Eligibility rules: must be in the settings list, prefer NULL
    last_checked_at (never checked), then oldest last_checked_at,
    skip if checked within cooldown_days. Returns None if no channel is due.
    """
    if not channels:
        return None

    channel_ids = [ch.channel_id for ch in channels]
    placeholders = ",".join("?" for _ in channel_ids)
    cutoff = datetime.now(UTC) - timedelta(days=cooldown_days)

    cursor = await conn.execute(
        f"""
        SELECT channel_id FROM agent_youtube_summary_channels
        WHERE channel_id IN ({placeholders})
          AND (last_checked_at IS NULL OR last_checked_at < ?)
        ORDER BY
            CASE WHEN last_checked_at IS NULL THEN 0 ELSE 1 END,
            last_checked_at ASC
        LIMIT 1
        """,
        (*channel_ids, cutoff.isoformat()),
    )
    row = await cursor.fetchone()
    return row["channel_id"] if row else None


async def video_exists_with_transcript(
    conn: aiosqlite.Connection,
    video_id: str,
) -> bool:
    """Check if a video exists in the items table and has a non-null transcript."""
    cursor = await conn.execute(
        """
        SELECT 1 FROM agent_youtube_summary_items
        WHERE video_id = ? AND transcript IS NOT NULL
        """,
        (video_id,),
    )
    return await cursor.fetchone() is not None


async def upsert_video(
    conn: aiosqlite.Connection,
    video_id: str,
    channel_id: str,
    channel_name: str | None,
    title: str,
    description: str | None,
    published_at: str | None,
    duration: str | None,
    view_count: int | None,
    like_count: int | None,
    comment_count: int | None,
    thumbnail_url: str | None,
    transcript: str | None,
    status: str,
) -> None:
    """Insert or replace a video row in the items table."""
    await conn.execute(
        """
        INSERT OR REPLACE INTO agent_youtube_summary_items
            (video_id, channel_id, channel_name, title, description,
             published_at, duration, view_count, like_count, comment_count,
             thumbnail_url, transcript, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            video_id,
            channel_id,
            channel_name,
            title,
            description,
            published_at,
            duration,
            view_count,
            like_count,
            comment_count,
            thumbnail_url,
            transcript,
            status,
        ),
    )
    await conn.commit()


async def update_channel_checked(
    conn: aiosqlite.Connection,
    channel_id: str,
) -> None:
    """Set last_checked_at to now for the given channel."""
    await conn.execute(
        """
        UPDATE agent_youtube_summary_channels
        SET last_checked_at = ?
        WHERE channel_id = ?
        """,
        (datetime.now(UTC).isoformat(), channel_id),
    )
    await conn.commit()


async def get_collected_items(conn: aiosqlite.Connection) -> list[dict]:
    """Return items with status 'collected' and a non-null transcript."""
    cursor = await conn.execute(
        """
        SELECT video_id, channel_id, channel_name, title, description,
               published_at, duration, view_count, like_count, comment_count,
               thumbnail_url, transcript, status
        FROM agent_youtube_summary_items
        WHERE status = 'collected' AND transcript IS NOT NULL
        """
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def insert_summary(
    conn: aiosqlite.Connection,
    video_id: str,
    summary: str,
    topics: list[str],
    key_points: list[str],
    model_used: str,
    prompt_version: str,
) -> None:
    """Insert a summary row, storing topics and key_points as JSON strings."""
    await conn.execute(
        """
        INSERT OR REPLACE INTO agent_youtube_summary_summaries
            (video_id, summary, topics, key_points, model_used, prompt_version)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            video_id,
            summary,
            json.dumps(topics),
            json.dumps(key_points),
            model_used,
            prompt_version,
        ),
    )
    await conn.commit()


async def update_item_status(
    conn: aiosqlite.Connection,
    video_id: str,
    status: str,
) -> None:
    """Update the status field on an item row."""
    await conn.execute(
        """
        UPDATE agent_youtube_summary_items
        SET status = ?
        WHERE video_id = ?
        """,
        (status, video_id),
    )
    await conn.commit()


async def get_todays_summaries(conn: aiosqlite.Connection) -> list[dict]:
    """Return today's summaries joined with item data, ordered by channel."""
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    cursor = await conn.execute(
        """
        SELECT
            i.video_id, i.channel_id, i.channel_name, i.title,
            i.description, i.published_at, i.duration, i.view_count,
            i.like_count, i.comment_count, i.thumbnail_url,
            s.summary, s.topics, s.key_points, s.model_used,
            s.prompt_version, s.summarized_at
        FROM agent_youtube_summary_summaries s
        JOIN agent_youtube_summary_items i ON s.video_id = i.video_id
        WHERE DATE(s.summarized_at) = ?
        ORDER BY i.channel_name, s.summarized_at DESC
        """,
        (today,),
    )
    rows = await cursor.fetchall()
    results = []
    for row in rows:
        item = dict(row)
        item["topics"] = json.loads(item["topics"]) if item["topics"] else []
        item["key_points"] = (
            json.loads(item["key_points"]) if item["key_points"] else []
        )
        results.append(item)
    return results
