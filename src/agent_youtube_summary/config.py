"""
Configuration for the agent-youtube-summary agent.

Loads infrastructure settings from environment variables via python-dotenv.
This is the single source of truth for all environment-driven configuration.
Other modules import from here — they never read os.environ directly.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
"""Resolved path to the Agent-YouTube-Summary project root directory."""

# Shared platform paths

WORKSPACE_DIR: str = os.environ.get("WORKSPACE_DIR", str(_PROJECT_ROOT.parent))
"""Path to the workspace root (for scanning Agent-*/ directories)."""

SHARED_DIR: str = os.environ.get("SHARED_DIR", str(_PROJECT_ROOT.parent / "shared"))
"""Path to the shared/ folder (CSS, templates)."""

DATA_DIR: str = os.environ.get("DATA_DIR", str(_PROJECT_ROOT.parent / "data"))
"""Path to the data/ directory (SQLite database, markdown outputs)."""

DB_PATH: str = os.environ.get("DB_PATH", os.path.join(DATA_DIR, "artimesone.db"))
"""Path to the shared SQLite database file."""

# Web server

HOST: str = os.environ.get("HOST", "127.0.0.1")
"""Server bind address."""

PORT: str = os.environ.get("PORT", "8001")
"""Server port."""

# Agent-specific

OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
"""OpenAI API key for Stage 2 summarization. Empty string disables LLM calls."""

ROLLUP_OUTPUT_DIR: str = os.path.join(DATA_DIR, "agent-youtube-summary")
"""Directory where daily rollup markdown files are written."""

SETTINGS_PATH: str = os.environ.get(
    "SETTINGS_PATH", str(_PROJECT_ROOT / "settings.json")
)
"""Path to the settings.json file."""

PROMPTS_DIR: str = os.environ.get("PROMPTS_DIR", str(_PROJECT_ROOT / "prompts"))
"""Directory containing prompt template files."""
