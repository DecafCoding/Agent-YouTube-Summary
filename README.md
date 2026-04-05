# Agent-YouTube-Summary

A YouTube channel monitoring agent that automatically collects new videos, generates LLM-powered summaries, and produces daily markdown rollups. Part of the [ArtimesOne](https://github.com/DecafCoding/ArtimesOne) platform.

## Overview

The agent runs a three-stage pipeline triggered by cron:

1. **Collect** — Selects the next eligible channel, fetches recent video metadata and transcripts via [utils-youtube](https://github.com/DecafCoding/Utils-YouTube), and stores everything in SQLite.
2. **Summarize** — Sends each collected transcript to a configurable LLM (default: `gpt-4o-mini`) for structured summarization (summary, topics, key points).
3. **Rollup** — Assembles today's summaries into a markdown digest grouped by channel.

## Project Structure

```
Agent-YouTube-Summary/
├── prompts/
│   └── summarize_video.md             # LLM prompt template
├── registry.json                      # Dashboard sidebar entry
├── settings.schema.json               # Dashboard-renderable settings schema
├── settings.json                      # Default settings values
├── widgets.schema.json                # Dashboard widget declarations
├── src/agent_youtube_summary/
│   ├── config.py                      # Env var loading
│   ├── settings.py                    # Settings loader and Pydantic models
│   ├── db.py                          # SQLite tables, upserts, queries
│   ├── stage_collect.py               # Stage 1 pipeline
│   ├── stage_summarize.py             # Stage 2 pipeline
│   ├── rollup.py                      # Markdown rollup generator
│   └── pipeline.py                    # Top-level orchestrator
└── tests/                             # 50 tests across 7 files
```

## Dependencies

This agent depends on [utils-youtube](https://github.com/DecafCoding/Utils-YouTube), a shared async library that handles all YouTube Data API and Apify interactions. Stage 1 imports directly from it for video discovery, metadata retrieval, and transcript extraction — keeping that infrastructure in one place so multiple agents (this one and [agent-youtube-research](https://github.com/DecafCoding/Agent-YouTube-Research)) share the same code.

`utils-youtube` is declared as a path dependency in `pyproject.toml` and expects both repos to live side-by-side in the same workspace:

```
AI Agents/
├── Agent-YouTube-Summary/
└── Utils-YouTube/
```

## Setup

```bash
# Install dependencies
uv sync --all-extras

# Copy and fill in env vars
cp .env.example .env

# Run the pipeline
uv run python -m agent_youtube_summary.pipeline
```

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for summarization |
| `DB_PATH` | Path to shared SQLite database (default: `../../data/artimesone.db`) |

YouTube and Apify API keys are managed by [utils-youtube](https://github.com/DecafCoding/Utils-YouTube) — see its documentation for setup.

## Configuration

All behavior is configurable via `settings.json` (editable through the ArtimesOne Dashboard):

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
