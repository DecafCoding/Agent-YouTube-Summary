# Agent-YouTube-Summary

A YouTube channel monitoring agent that automatically collects new videos, generates LLM-powered summaries, and produces daily markdown rollups. Part of the [ArtimesOne](https://github.com/DecafCoding/ArtimesOne) platform.

## Overview

The agent runs a three-stage pipeline triggered by cron:

1. **Collect** — Selects the next eligible channel, fetches recent video metadata and transcripts via [utils-youtube](https://github.com/DecafCoding/Utils-YouTube), and stores everything in SQLite.
2. **Summarize** — Sends each collected transcript to a configurable LLM (default: `gpt-4o-mini`) for structured summarization (summary, topics, key points).
3. **Rollup** — Assembles today's summaries into a markdown digest grouped by channel.

The agent also runs as a FastAPI web application with a settings page and rollup viewer, extending the shared ArtimesOne base template for a consistent sidebar and visual identity across all platform apps.

## Project Structure

```
Agent-YouTube-Summary/
├── prompts/
│   └── summarize_video.md                 # LLM prompt template
├── templates/
│   ├── settings.html                      # Settings form (schema-driven)
│   ├── rollups.html                       # Rollup list page
│   └── rollup_detail.html                 # Single rollup view
├── registry.json                          # Sidebar entry (id, name, url)
├── settings.schema.json                   # JSON Schema for settings form rendering
├── settings.json                          # Current settings values
├── widgets.schema.json                    # Dashboard widget declarations
├── src/agent_youtube_summary/
│   ├── config.py                          # Env var loading (shared + agent-specific)
│   ├── settings.py                        # Settings loader and Pydantic models
│   ├── db.py                              # SQLite tables, upserts, queries
│   ├── stage_collect.py                   # Stage 1 — video collection
│   ├── stage_summarize.py                 # Stage 2 — LLM summarization
│   ├── rollup.py                          # Stage 3 — markdown rollup generator
│   ├── pipeline.py                        # Top-level pipeline orchestrator
│   ├── app.py                             # FastAPI web application
│   ├── discovery.py                       # Re-exports discover_agents from utils-artimesone
│   └── routes/
│       ├── settings_page.py               # GET/POST /settings
│       └── rollups.py                     # GET /rollups, /rollups/{date}
└── tests/                                 # 66 tests across 9 files
```

## Dependencies

This agent depends on two shared libraries:

- [utils-youtube](https://github.com/DecafCoding/Utils-YouTube) — Async library for YouTube Data API and Apify transcript interactions. Stage 1 imports directly from it for video discovery, metadata retrieval, and transcript extraction.
- [utils-artimesone](https://github.com/DecafCoding/Utils-ArtimesOne) — Shared platform utilities for workspace discovery, settings I/O, and database connectivity. Provides `discover_agents()` used by the sidebar.

Both are declared as path dependencies in `pyproject.toml` and expect all repos to live side-by-side in the same workspace:

```
AI Agents/
├── shared/                    # Shared CSS and Jinja2 base template
├── data/                      # Shared SQLite database and markdown outputs
├── Agent-YouTube-Summary/
├── Utils-YouTube/
└── Utils-ArtimesOne/
```

## Setup

```bash
# Install dependencies
uv sync --all-extras

# Copy and fill in env vars
cp .env.example .env

# Run the pipeline
uv run python -m agent_youtube_summary.pipeline

# Start the web UI
uv run python -m agent_youtube_summary.app
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `WORKSPACE_DIR` | Yes | Path to the workspace root (default: `..`) |
| `SHARED_DIR` | Yes | Path to `shared/` folder for CSS and templates (default: `../shared`) |
| `DB_PATH` | Yes | Path to shared SQLite database (default: `../data/artimesone.db`) |
| `DATA_DIR` | Yes | Path to `data/` directory for markdown outputs (default: `../data`) |
| `HOST` | No | Server bind address (default: `127.0.0.1`) |
| `PORT` | No | Server port (default: `8001`) |
| `OPENAI_API_KEY` | Yes | OpenAI API key for summarization |

YouTube and Apify API keys are managed by [utils-youtube](https://github.com/DecafCoding/Utils-YouTube) — see its documentation for setup.

## Web UI

The agent runs on `http://localhost:8001` with:

- **Settings page** (`/settings`) — Form rendered dynamically from `settings.schema.json`. Saves to `settings.json` via async POST with no page reload.
- **Rollup viewer** (`/rollups`) — Lists daily markdown rollup files. Click a date to view the full digest.
- **Sidebar** — Discovered automatically from `Agent-*/registry.json` files in the workspace. Links navigate between apps on different ports.

## Configuration

All behavior is configurable via `settings.json` (editable through the settings page or the ArtimesOne Dashboard):

- **channels** — YouTube channels to monitor
- **schedule** — Cron expression for collection frequency
- **channelCooldownDays** — Minimum days between checks per channel
- **maxVideosPerChannel** — Recent videos to fetch per check
- **maxTranscriptDurationMinutes** — Skip videos longer than this
- **summaryModel** — LLM model for summarization

## Testing

```bash
uv run pytest tests/ -v
```
