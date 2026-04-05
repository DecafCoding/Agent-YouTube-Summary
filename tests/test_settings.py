"""
Tests for the settings loader.

Validates loading from valid JSON, fallback on missing file, and
fallback on invalid JSON.
"""

import json

from agent_youtube_summary.settings import SummarySettings, load_settings


class TestLoadSettings:
    """Tests for the load_settings function."""

    async def test_loads_valid_settings_file(
        self, tmp_path, monkeypatch, sample_settings_json
    ):
        """Valid settings.json is loaded and parsed correctly."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(sample_settings_json)
        monkeypatch.setattr(
            "agent_youtube_summary.settings.SETTINGS_PATH", str(settings_file)
        )

        result = await load_settings()

        assert len(result.channels) == 2
        assert result.channels[0].channel_id == "UCYO_jab_esuFRV4b17AJtAw"
        assert result.channels[0].name == "3Blue1Brown"
        assert result.channels[1].channel_id == "UCsBjURrPoezykLs9EqgamOA"
        assert result.channel_cooldown_days == 3
        assert result.max_videos_per_channel == 5
        assert result.max_transcript_duration_minutes == 60
        assert result.summary_model == "gpt-4o-mini"

    async def test_returns_defaults_when_file_missing(self, tmp_path, monkeypatch):
        """Missing settings file returns default SummarySettings."""
        monkeypatch.setattr(
            "agent_youtube_summary.settings.SETTINGS_PATH",
            str(tmp_path / "nonexistent.json"),
        )

        result = await load_settings()

        assert isinstance(result, SummarySettings)
        assert result.channels == []
        assert result.channel_cooldown_days == 3
        assert result.summary_model == "gpt-4o-mini"

    async def test_returns_defaults_on_invalid_json(self, tmp_path, monkeypatch):
        """Malformed JSON falls back to default SummarySettings."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{invalid json!!}")
        monkeypatch.setattr(
            "agent_youtube_summary.settings.SETTINGS_PATH", str(settings_file)
        )

        result = await load_settings()

        assert isinstance(result, SummarySettings)
        assert result.channels == []

    async def test_partial_settings_uses_defaults_for_missing_fields(
        self, tmp_path, monkeypatch
    ):
        """Settings file with only channels uses defaults for other fields."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(
            json.dumps(
                {"channels": [{"channelId": "UCtest123", "name": "Test Channel"}]}
            )
        )
        monkeypatch.setattr(
            "agent_youtube_summary.settings.SETTINGS_PATH", str(settings_file)
        )

        result = await load_settings()

        assert len(result.channels) == 1
        assert result.channel_cooldown_days == 3
        assert result.max_videos_per_channel == 5
        assert result.schedule == "0 */1 * * *"
