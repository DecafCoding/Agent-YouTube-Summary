"""Tests for the workspace discovery module."""

import json
from pathlib import Path

from agent_youtube_summary.discovery import DASHBOARD_ENTRY, discover_agents


def _create_agent(tmp_path: Path, name: str, registry: dict | None = None) -> None:
    """Create a fake Agent-* directory with an optional registry.json."""
    agent_dir = tmp_path / name
    agent_dir.mkdir()
    if registry is not None:
        (agent_dir / "registry.json").write_text(json.dumps(registry), encoding="utf-8")


class TestDiscoverAgents:
    """Tests for discover_agents()."""

    def test_discovers_agents_from_valid_registries(self, tmp_path: Path) -> None:
        """Happy path — discovers two agents plus Dashboard."""
        _create_agent(
            tmp_path,
            "Agent-Foo",
            {
                "id": "agent-foo",
                "name": "Foo Agent",
                "category": "Agent",
                "icon": "star",
                "url": "http://localhost:8001",
            },
        )
        _create_agent(
            tmp_path,
            "Agent-Bar",
            {
                "id": "agent-bar",
                "name": "Bar Agent",
                "category": "Agent",
                "icon": "bolt",
                "url": "http://localhost:8002",
            },
        )

        result = discover_agents(str(tmp_path))

        assert len(result) == 3
        assert result[0]["id"] == "artimesone"
        agent_names = [a["name"] for a in result[1:]]
        assert agent_names == ["Bar Agent", "Foo Agent"]

    def test_skips_directory_without_registry(self, tmp_path: Path) -> None:
        """Directories missing registry.json are skipped."""
        _create_agent(tmp_path, "Agent-NoReg")
        _create_agent(
            tmp_path,
            "Agent-Valid",
            {
                "id": "agent-valid",
                "name": "Valid",
                "category": "Agent",
                "icon": "check",
                "url": "http://localhost:8001",
            },
        )

        result = discover_agents(str(tmp_path))

        assert len(result) == 2
        assert result[1]["id"] == "agent-valid"

    def test_skips_invalid_json(self, tmp_path: Path) -> None:
        """Malformed JSON in registry.json is skipped with a warning."""
        agent_dir = tmp_path / "Agent-Bad"
        agent_dir.mkdir()
        (agent_dir / "registry.json").write_text("not valid json", encoding="utf-8")

        result = discover_agents(str(tmp_path))

        assert len(result) == 1
        assert result[0]["id"] == "artimesone"

    def test_skips_non_directory_matching_pattern(self, tmp_path: Path) -> None:
        """Files matching Agent-* pattern are not treated as agents."""
        (tmp_path / "Agent-File.txt").write_text("not a dir", encoding="utf-8")

        result = discover_agents(str(tmp_path))

        assert len(result) == 1

    def test_empty_workspace_returns_only_dashboard(self, tmp_path: Path) -> None:
        """Empty workspace returns only the Dashboard entry."""
        result = discover_agents(str(tmp_path))

        assert len(result) == 1
        assert result[0] == DASHBOARD_ENTRY

    def test_sort_order_platform_first_then_alphabetical(self, tmp_path: Path) -> None:
        """Platform category comes first, then Agents sorted alphabetically."""
        _create_agent(
            tmp_path,
            "Agent-Zebra",
            {
                "id": "agent-zebra",
                "name": "Zebra",
                "category": "Agent",
                "icon": "z",
                "url": "http://localhost:8003",
            },
        )
        _create_agent(
            tmp_path,
            "Agent-Alpha",
            {
                "id": "agent-alpha",
                "name": "Alpha",
                "category": "Agent",
                "icon": "a",
                "url": "http://localhost:8001",
            },
        )

        result = discover_agents(str(tmp_path))

        assert result[0]["category"] == "Platform"
        assert result[1]["name"] == "Alpha"
        assert result[2]["name"] == "Zebra"

    def test_skips_registry_with_missing_required_fields(self, tmp_path: Path) -> None:
        """Registry files missing required fields are skipped."""
        _create_agent(
            tmp_path,
            "Agent-Incomplete",
            {
                "id": "agent-incomplete",
                "name": "Incomplete",
            },
        )

        result = discover_agents(str(tmp_path))

        assert len(result) == 1
