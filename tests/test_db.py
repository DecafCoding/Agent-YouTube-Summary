"""
Tests for the database layer.

Uses in-memory SQLite for fast, isolated tests. Covers table creation,
channel sync, next-channel selection, upsert deduplication, status
transitions, and today's summaries query.
"""

from datetime import UTC, datetime, timedelta

import aiosqlite
import pytest

from agent_youtube_summary.db import (
    ensure_tables,
    get_collected_items,
    get_next_channel,
    get_todays_summaries,
    insert_summary,
    sync_channels,
    update_item_status,
    upsert_video,
    video_exists_with_transcript,
)


@pytest.fixture()
async def db():
    """Provide an in-memory database with tables created."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await ensure_tables(conn)
    yield conn
    await conn.close()


class TestEnsureTables:
    """Tests for table creation."""

    async def test_creates_all_three_tables(self, db):
        """All three agent tables are created."""
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row["name"] for row in await cursor.fetchall()]
        assert "agent_youtube_summary_channels" in tables
        assert "agent_youtube_summary_items" in tables
        assert "agent_youtube_summary_summaries" in tables

    async def test_idempotent_creation(self, db):
        """Calling ensure_tables twice does not raise."""
        await ensure_tables(db)


class TestSyncChannels:
    """Tests for the channel sync operation."""

    async def test_inserts_new_channels(self, db, sample_channels):
        """Channels from settings are inserted into the table."""
        await sync_channels(db, sample_channels)
        cursor = await db.execute(
            "SELECT channel_id, name FROM agent_youtube_summary_channels"
        )
        rows = await cursor.fetchall()
        assert len(rows) == 2
        ids = {row["channel_id"] for row in rows}
        assert "UCYO_jab_esuFRV4b17AJtAw" in ids
        assert "UCsBjURrPoezykLs9EqgamOA" in ids

    async def test_does_not_duplicate_existing_channels(self, db, sample_channels):
        """Re-syncing the same channels produces no duplicates."""
        await sync_channels(db, sample_channels)
        await sync_channels(db, sample_channels)
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM agent_youtube_summary_channels"
        )
        row = await cursor.fetchone()
        assert row["cnt"] == 2


class TestGetNextChannel:
    """Tests for next-channel priority queue."""

    async def test_returns_unchecked_channel_first(self, db, sample_channels):
        """Channels with NULL last_checked_at are returned first."""
        await sync_channels(db, sample_channels)
        result = await get_next_channel(db, sample_channels, cooldown_days=3)
        assert result in {ch.channel_id for ch in sample_channels}

    async def test_returns_oldest_checked_channel(self, db, sample_channels):
        """After all checked, returns the one with oldest last_checked_at."""
        await sync_channels(db, sample_channels)
        old_time = (datetime.now(UTC) - timedelta(days=10)).isoformat()
        recent_time = (datetime.now(UTC) - timedelta(days=5)).isoformat()
        await db.execute(
            "UPDATE agent_youtube_summary_channels"
            " SET last_checked_at = ? WHERE channel_id = ?",
            (old_time, sample_channels[0].channel_id),
        )
        await db.execute(
            "UPDATE agent_youtube_summary_channels"
            " SET last_checked_at = ? WHERE channel_id = ?",
            (recent_time, sample_channels[1].channel_id),
        )
        await db.commit()

        result = await get_next_channel(db, sample_channels, cooldown_days=3)
        assert result == sample_channels[0].channel_id

    async def test_returns_none_when_all_within_cooldown(self, db, sample_channels):
        """Returns None if all channels were checked within cooldown."""
        await sync_channels(db, sample_channels)
        now = datetime.now(UTC).isoformat()
        for ch in sample_channels:
            await db.execute(
                "UPDATE agent_youtube_summary_channels"
                " SET last_checked_at = ? WHERE channel_id = ?",
                (now, ch.channel_id),
            )
        await db.commit()

        result = await get_next_channel(db, sample_channels, cooldown_days=3)
        assert result is None

    async def test_returns_none_for_empty_channel_list(self, db):
        """Returns None when no channels are configured."""
        result = await get_next_channel(db, [], cooldown_days=3)
        assert result is None


class TestUpsertVideo:
    """Tests for video upsert and existence checks."""

    async def test_inserts_new_video(self, db):
        """A new video is inserted into the items table."""
        await upsert_video(
            db,
            video_id="vid1",
            channel_id="ch1",
            channel_name="Channel 1",
            title="Test Video",
            description="A test",
            published_at="2025-01-15T10:30:00+00:00",
            duration="PT12M30S",
            view_count=1000,
            like_count=50,
            comment_count=10,
            thumbnail_url="https://example.com/thumb.jpg",
            transcript="Hello world",
            status="collected",
        )
        cursor = await db.execute(
            "SELECT * FROM agent_youtube_summary_items WHERE video_id = 'vid1'"
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["title"] == "Test Video"
        assert row["transcript"] == "Hello world"

    async def test_upsert_updates_existing_video(self, db):
        """Upserting the same video_id updates the row."""
        await upsert_video(
            db,
            "vid1",
            "ch1",
            "Channel",
            "Original",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "collected",
        )
        await upsert_video(
            db,
            "vid1",
            "ch1",
            "Channel",
            "Updated",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "transcript",
            "collected",
        )
        cursor = await db.execute(
            "SELECT title, transcript FROM agent_youtube_summary_items"
            " WHERE video_id = 'vid1'"
        )
        row = await cursor.fetchone()
        assert row["title"] == "Updated"
        assert row["transcript"] == "transcript"

    async def test_video_exists_with_transcript_true(self, db):
        """Returns True when video exists with a transcript."""
        await upsert_video(
            db,
            "vid1",
            "ch1",
            "Ch",
            "Title",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "transcript text",
            "collected",
        )
        assert await video_exists_with_transcript(db, "vid1") is True

    async def test_video_exists_with_transcript_false_no_transcript(self, db):
        """Returns False when video exists but has no transcript."""
        await upsert_video(
            db,
            "vid1",
            "ch1",
            "Ch",
            "Title",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "skipped",
        )
        assert await video_exists_with_transcript(db, "vid1") is False

    async def test_video_exists_with_transcript_false_missing(self, db):
        """Returns False when video does not exist."""
        assert await video_exists_with_transcript(db, "nonexistent") is False


class TestStatusTransitions:
    """Tests for item status updates."""

    async def test_update_status_to_summarized(self, db):
        """Status can be updated from collected to summarized."""
        await upsert_video(
            db,
            "vid1",
            "ch1",
            "Ch",
            "Title",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "transcript",
            "collected",
        )
        await update_item_status(db, "vid1", "summarized")
        cursor = await db.execute(
            "SELECT status FROM agent_youtube_summary_items WHERE video_id = 'vid1'"
        )
        row = await cursor.fetchone()
        assert row["status"] == "summarized"


class TestSummaries:
    """Tests for summary insertion and today's summaries query."""

    async def test_insert_and_retrieve_summary(self, db):
        """Inserted summary is retrievable with deserialized JSON fields."""
        await upsert_video(
            db,
            "vid1",
            "ch1",
            "Channel",
            "Title",
            "Desc",
            "2025-01-15T10:30:00",
            "PT12M30S",
            1000,
            50,
            10,
            "https://thumb.jpg",
            "transcript",
            "summarized",
        )
        await insert_summary(
            db,
            video_id="vid1",
            summary="A great video about Python.",
            topics=["Python", "coding"],
            key_points=["Point 1", "Point 2"],
            model_used="gpt-4o-mini",
            prompt_version="v1",
        )

        summaries = await get_todays_summaries(db)
        assert len(summaries) == 1
        assert summaries[0]["summary"] == "A great video about Python."
        assert summaries[0]["topics"] == ["Python", "coding"]
        assert summaries[0]["key_points"] == ["Point 1", "Point 2"]
        assert summaries[0]["model_used"] == "gpt-4o-mini"

    async def test_no_summaries_today_returns_empty(self, db):
        """Returns empty list when no summaries exist for today."""
        summaries = await get_todays_summaries(db)
        assert summaries == []


class TestGetCollectedItems:
    """Tests for retrieving items ready for summarization."""

    async def test_returns_collected_with_transcript(self, db):
        """Returns only items with status 'collected' and non-null transcript."""
        await upsert_video(
            db,
            "vid1",
            "ch1",
            "Ch",
            "Collected",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "transcript",
            "collected",
        )
        await upsert_video(
            db,
            "vid2",
            "ch1",
            "Ch",
            "Skipped",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "skipped",
        )
        await upsert_video(
            db,
            "vid3",
            "ch1",
            "Ch",
            "Summarized",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "transcript",
            "summarized",
        )

        items = await get_collected_items(db)
        assert len(items) == 1
        assert items[0]["video_id"] == "vid1"
