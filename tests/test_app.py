"""Tests for the FastAPI web application routes."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from agent_youtube_summary.app import app

MOCK_SIDEBAR = [
    {
        "id": "artimesone",
        "name": "Dashboard",
        "category": "Platform",
        "icon": "home",
        "url": "http://localhost:8000",
    },
    {
        "id": "agent-youtube-summary",
        "name": "YouTube Summary",
        "category": "Agent",
        "icon": "youtube",
        "url": "http://localhost:8001",
    },
]


@pytest.fixture()
def client() -> TestClient:
    """TestClient with mocked sidebar discovery."""
    with patch("agent_youtube_summary.app.discover_agents", return_value=MOCK_SIDEBAR):
        yield TestClient(app)


class TestHome:
    """Tests for the home route."""

    def test_home_redirects_to_rollups(self, client: TestClient) -> None:
        """GET / redirects to /rollups."""
        resp = client.get("/", follow_redirects=False)

        assert resp.status_code == 302
        assert resp.headers["location"] == "/rollups"


class TestSettingsPage:
    """Tests for the settings page routes."""

    def test_get_settings_returns_200(self, client: TestClient) -> None:
        """GET /settings returns 200 with HTML containing form."""
        resp = client.get("/settings")

        assert resp.status_code == 200
        assert "settings-form" in resp.text

    def test_post_settings_saves_valid_json(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """POST /settings with valid JSON saves to settings.json."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{}", encoding="utf-8")

        with patch(
            "agent_youtube_summary.routes.settings_page._SETTINGS_FILE",
            settings_file,
        ):
            data = {"schedule": "0 */2 * * *", "channelCooldownDays": 5}
            resp = client.post("/settings", json=data)

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

        saved = json.loads(settings_file.read_text(encoding="utf-8"))
        assert saved["schedule"] == "0 */2 * * *"
        assert saved["channelCooldownDays"] == 5

    def test_post_settings_rejects_invalid_body(self, client: TestClient) -> None:
        """POST /settings with non-JSON body returns error."""
        resp = client.post(
            "/settings",
            content=b"not json",
            headers={"content-type": "application/json"},
        )

        assert resp.status_code == 400
        assert resp.json()["status"] == "error"


class TestRollupsPage:
    """Tests for the rollup viewer routes."""

    def test_get_rollups_returns_200(self, client: TestClient) -> None:
        """GET /rollups returns 200 with HTML."""
        resp = client.get("/rollups")

        assert resp.status_code == 200
        assert "Rollups" in resp.text

    def test_rollups_lists_files(self, client: TestClient, tmp_path: Path) -> None:
        """GET /rollups with rollup files shows them listed."""
        rollup_dir = tmp_path / "rollups"
        rollup_dir.mkdir()
        (rollup_dir / "2026-04-05.md").write_text("# Rollup", encoding="utf-8")
        (rollup_dir / "2026-04-04.md").write_text("# Rollup", encoding="utf-8")

        with patch(
            "agent_youtube_summary.routes.rollups.ROLLUP_OUTPUT_DIR",
            str(rollup_dir),
        ):
            resp = client.get("/rollups")

        assert resp.status_code == 200
        assert "2026-04-05" in resp.text
        assert "2026-04-04" in resp.text

    def test_rollups_empty_state(self, client: TestClient, tmp_path: Path) -> None:
        """GET /rollups with no files shows empty state message."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with patch(
            "agent_youtube_summary.routes.rollups.ROLLUP_OUTPUT_DIR",
            str(empty_dir),
        ):
            resp = client.get("/rollups")

        assert resp.status_code == 200
        assert "No rollups yet" in resp.text

    def test_rollup_detail_existing_file(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """GET /rollups/{date} with existing file returns 200 with content."""
        rollup_dir = tmp_path / "rollups"
        rollup_dir.mkdir()
        (rollup_dir / "2026-04-05.md").write_text(
            "# YouTube Summary — 2026-04-05", encoding="utf-8"
        )

        with patch(
            "agent_youtube_summary.routes.rollups.ROLLUP_OUTPUT_DIR",
            str(rollup_dir),
        ):
            resp = client.get("/rollups/2026-04-05")

        assert resp.status_code == 200
        assert "YouTube Summary" in resp.text

    def test_rollup_detail_missing_file(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """GET /rollups/{date} with missing file returns 404."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with patch(
            "agent_youtube_summary.routes.rollups.ROLLUP_OUTPUT_DIR",
            str(empty_dir),
        ):
            resp = client.get("/rollups/2026-04-05")

        assert resp.status_code == 404
        assert "not found" in resp.text.lower()
