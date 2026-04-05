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

DB_PATH: str = os.environ.get("DB_PATH", "../../data/artimesone.db")
"""Path to the shared SQLite database file."""

OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
"""OpenAI API key for Stage 2 summarization. Empty string disables LLM calls."""

ROLLUP_OUTPUT_DIR: str = os.environ.get(
    "ROLLUP_OUTPUT_DIR", "../../data/agent-youtube-summary"
)
"""Directory where daily rollup markdown files are written."""

SETTINGS_PATH: str = os.environ.get(
    "SETTINGS_PATH", str(_PROJECT_ROOT / "settings.json")
)
"""Path to the settings.json file."""

PROMPTS_DIR: str = os.environ.get("PROMPTS_DIR", str(_PROJECT_ROOT / "prompts"))
"""Directory containing prompt template files."""
