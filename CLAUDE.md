# CLAUDE.md — Agent-YouTube-Summary

Project-specific conventions for the YouTube Summary Agent. The root `CLAUDE.md` covers workspace-wide standards; this file covers what's specific to this project.

---

## What This Project Is

The YouTube Summary Agent monitors configured YouTube channels for new videos on a schedule. It runs on `localhost:8001` and follows the two-stage pipeline pattern:

- **Stage 1 (Collect)** — Deterministic. Picks the next eligible channel based on cooldown, fetches recent videos via `utils-youtube`, retrieves transcripts via Apify, and stores everything in the shared SQLite database.
- **Stage 2 (Summarize + Rollup)** — LLM-powered. Summarizes each collected video using an LLM, then aggregates the day's summaries into a markdown rollup document.

The pipeline is callable standalone (`python -m agent_youtube_summary.pipeline`) independent of the Dashboard scheduler.

## Key Rules

1. **Two-stage pipeline.** Collect is deterministic (no LLM). Summarize and rollup use an LLM.
2. **One channel per pipeline run.** `get_next_channel()` picks the next eligible channel based on cooldown — the pipeline does not process all channels at once.
3. **Pipeline is standalone.** `python -m agent_youtube_summary.pipeline` runs independently of the Dashboard scheduler.
4. **Settings use camelCase in JSON** (matching `settings.schema.json`) but **snake_case in Python** (via Pydantic aliases).
5. **All table names prefixed with `agent_youtube_summary_`.**
6. **Uses `utils-youtube`** for YouTube API and Apify calls — never calls these APIs directly.
7. **Uses `utils-artimesone`** for discovery, settings I/O, and database connections.

## Module Map

| Module | Purpose |
|--------|---------|
| `config.py` | Environment variable loading (DB_PATH, DATA_DIR, WORKSPACE_DIR, SHARED_DIR, PORT, API keys) |
| `settings.py` | Pydantic models (ChannelConfig, SummarySettings) + load_settings() from settings.json |
| `discovery.py` | Re-exports shared discover_agents from utils-artimesone |
| `db.py` | SQLite table definitions (channels, items, summaries) + all CRUD operations |
| `stage_collect.py` | Stage 1: fetch recent videos from next eligible channel, fetch transcripts, store in SQLite |
| `stage_summarize.py` | Stage 2: LLM summarization of collected videos with transcripts |
| `rollup.py` | Daily rollup: aggregate today's summaries into a markdown document |
| `pipeline.py` | Orchestrator: runs collect -> summarize -> rollup sequentially |
| `app.py` | FastAPI app with shared CSS mount, Jinja2 templates, sidebar context |
| `routes/settings_page.py` | Settings form: GET renders from schema, POST saves to settings.json |
| `routes/rollups.py` | Rollup viewer pages |

## Port Assignment

The YouTube Summary Agent runs on port **8001** (configured via `PORT` in `.env`).

## Dependencies

- `utils-artimesone` — shared platform utilities (discovery, settings, db)
- `utils-youtube` — YouTube Data API v3 and Apify transcript extraction
- `openai` — LLM API client for Stage 2 summarization
- `aiosqlite` — async SQLite access
- `python-dotenv` — environment variable loading
- `pydantic` — settings validation with camelCase/snake_case aliasing
- `fastapi`, `uvicorn`, `jinja2` — web framework

## Testing

Tests use `pytest` + `pytest-asyncio` with `asyncio_mode = "auto"`. Mock all external API calls (YouTube, Apify, OpenAI). Route tests use FastAPI TestClient.
