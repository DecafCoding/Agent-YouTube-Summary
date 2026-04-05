# Feature: Agent YouTube Summary — Full Implementation

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Build the complete `agent-youtube-summary` agent: a two-stage pipeline that monitors YouTube channels for new videos, collects metadata and transcripts, produces LLM-powered per-video summaries, and generates daily markdown rollups. The agent follows the ArtimesOne contract (registry, settings schema, widgets) and depends on the shared `utils-youtube` library for all YouTube API and Apify interactions.

## User Story

As an ArtimesOne operator
I want the agent to automatically monitor YouTube channels, summarize new videos, and produce daily rollups
So that I can stay current on channel content without watching every video

## Problem Statement

Staying current across multiple YouTube channels is time-consuming. The operator needs an automated pipeline that discovers new videos, extracts their content, produces concise summaries, and assembles them into a scannable daily digest — all configurable via the Dashboard.

## Solution Statement

A three-stage pipeline (collect → summarize → rollup) triggered by cron. Stage 1 deterministically fetches metadata and transcripts via `utils-youtube`. Stage 2 sends transcripts to a configurable LLM for structured summarization. The rollup stage assembles today's summaries into a markdown file. SQLite stores all data; the ArtimesOne contract (settings, widgets, registry) enables Dashboard integration.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: High
**Primary Systems Affected**: Agent-YouTube-Summary (new), Utils-YouTube (dependency, no changes)
**Dependencies**: utils-youtube, openai SDK, aiosqlite, python-dotenv, pydantic

---

## CONTEXT REFERENCES

### Relevant Codebase Files — YOU MUST READ THESE BEFORE IMPLEMENTING

- `Utils-YouTube/src/utils_youtube/__init__.py` (lines 1-30) — Why: Public API surface. These are the exact imports the agent will use.
- `Utils-YouTube/src/utils_youtube/models.py` (lines 1-42) — Why: `VideoMetadata` model fields that map to the agent's SQLite columns. Field names must match exactly.
- `Utils-YouTube/src/utils_youtube/youtube_api.py` (lines 58-104) — Why: `fetch_recent_video_ids()` signature and return type. Used in Stage 1.
- `Utils-YouTube/src/utils_youtube/youtube_api.py` (lines 107-183) — Why: `fetch_video_details()` signature and return type. Used in Stage 1.
- `Utils-YouTube/src/utils_youtube/apify.py` (lines 27-58) — Why: `fetch_transcripts()` signature and return type (`dict[str, str]`). Used in Stage 1.
- `Utils-YouTube/src/utils_youtube/parsing.py` (lines 91-109) — Why: `duration_seconds()` function. Used for duration filtering in Stage 1.
- `Utils-YouTube/src/utils_youtube/config.py` (lines 1-35) — Why: Config pattern to mirror in the agent's own `config.py`.
- `Utils-YouTube/pyproject.toml` (lines 1-38) — Why: Project structure, build system (hatchling), ruff config, and pytest config patterns to replicate.
- `Utils-YouTube/tests/conftest.py` (lines 1-148) — Why: Fixture patterns for test setup.
- `Utils-YouTube/tests/test_youtube_api.py` (lines 1-263) — Why: Test patterns — class-based organization, respx mocking, monkeypatch usage.
- `Docs/PRD_agent_youtube_summary.md` — Why: The full PRD with all requirements, schema definitions, pipeline flow, and folder structure.
- `Docs/artimesone-architecture.md` — Why: Contract definitions (registry, settings, widgets, store) and table naming conventions.
- `CLAUDE.md` — Why: Workspace-wide coding standards (async patterns, error handling, logging, type hints, naming).

### New Files to Create

```
Agent-YouTube-Summary/
├── pyproject.toml                     # Package config, dependencies, ruff, pytest
├── .env.example                       # Documented env vars (YOUTUBE_API_KEY, APIFY_API_KEY, OPENAI_API_KEY, DB_PATH)
├── .gitignore                         # Already exists — may need updates for data/, .env
├── prompts/
│   └── summarize_video.md             # LLM prompt template with {{variables}}
├── registry.json                      # Dashboard sidebar entry
├── settings.schema.json               # Dashboard-renderable settings schema
├── settings.json                      # Default settings values
├── widgets.schema.json                # Dashboard widget declarations
├── src/
│   └── agent_youtube_summary/
│       ├── __init__.py                # Package docstring and public exports
│       ├── config.py                  # Env var loading (DB_PATH, OPENAI_API_KEY)
│       ├── db.py                      # SQLite table creation, upserts, queries
│       ├── settings.py                # Load and validate settings.json
│       ├── stage_collect.py           # Stage 1 pipeline entry point
│       ├── stage_summarize.py         # Stage 2 pipeline entry point
│       ├── rollup.py                  # Markdown rollup generator
│       └── pipeline.py                # Top-level orchestrator: collect → summarize → rollup
└── tests/
    ├── __init__.py
    ├── conftest.py                    # Shared fixtures (sample settings, DB setup, mock data)
    ├── test_db.py                     # Database layer tests
    ├── test_settings.py               # Settings loading tests
    ├── test_stage_collect.py          # Stage 1 pipeline tests
    ├── test_stage_summarize.py        # Stage 2 pipeline tests
    ├── test_rollup.py                 # Rollup generation tests
    └── test_pipeline.py               # Integration pipeline tests
```

### Relevant Documentation — READ BEFORE IMPLEMENTING

- OpenAI Python SDK: https://platform.openai.com/docs/api-reference/chat/create
  - Specific section: Async client, chat completions, JSON mode / response_format
  - Why: Stage 2 uses `openai.AsyncOpenAI().chat.completions.create()` for summarization
- aiosqlite: https://aiosqlite.omnilib.dev/en/stable/
  - Specific section: Connection management, async context managers
  - Why: All DB operations must be async per CLAUDE.md conventions
- Pydantic v2: https://docs.pydantic.dev/latest/
  - Specific section: BaseModel, Field(), model_config
  - Why: Settings model and any agent-specific data models

### Patterns to Follow

**Naming Conventions** (from CLAUDE.md):
- Modules: `snake_case` (e.g., `stage_collect.py`, `stage_summarize.py`)
- Classes: `PascalCase` (e.g., `SummarySettings`, `ChannelState`)
- Functions: `snake_case` (e.g., `sync_channels`, `get_next_channel`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DB_PATH`, `OPENAI_API_KEY`)
- Private: Leading underscore (e.g., `_ensure_tables`)

**Config Pattern** (mirror `Utils-YouTube/src/utils_youtube/config.py`):
```python
import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH: str = os.environ.get("DB_PATH", "../../data/artimesone.db")
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
```

**Logging Pattern** (from CLAUDE.md):
```python
import logging

logger = logging.getLogger(__name__)
```

**Error Handling Pattern** (mirror utils-youtube):
- Catch specific exceptions
- Log with context via `extra={}`
- Return graceful defaults (empty lists, None) instead of crashing
- Never catch bare `Exception` or `BaseException`

**Async I/O Pattern** (from CLAUDE.md):
- All I/O functions are `async`
- Use `aiosqlite` for database, not synchronous sqlite3
- Use `openai.AsyncOpenAI` for LLM calls
- Use `asyncio.gather()` where operations are independent

**Test Pattern** (mirror `Utils-YouTube/tests/`):
- Class-based test organization (`class TestSyncChannels:`)
- Fixtures in `conftest.py` for shared data
- `monkeypatch` for config overrides
- `pytest-asyncio` with `asyncio_mode = "auto"`
- Mock all external calls (DB via in-memory SQLite, LLM via mock)
- Descriptive test names: `test_collect_skips_video_when_duration_exceeds_limit`

**SQLite Table Prefix**: `agent_youtube_summary_` (from architecture doc)

---

## IMPLEMENTATION PLAN

### Task 1: Project Scaffolding and Configuration

Set up the project structure, dependencies, and configuration layer. This is the foundation everything else builds on.

- **CREATE**: `pyproject.toml` with:
  - Package name: `agent-youtube-summary`
  - Python: `>=3.12`
  - Dependencies: `utils-youtube` (path dependency: `{path = "../Utils-YouTube", editable = true}`), `openai>=1.60,<2.0`, `aiosqlite>=0.20,<1.0`, `python-dotenv>=1.0,<2.0`, `pydantic>=2.0,<3.0`
  - Dev dependencies: `pytest>=8.0`, `pytest-asyncio>=0.25`, `ruff`
  - Build system: hatchling (mirror Utils-YouTube)
  - `[tool.hatch.build.targets.wheel] packages = ["src/agent_youtube_summary"]`
  - Ruff config: `line-length = 88`, `target-version = "py312"`, `select = ["E", "F", "I", "W"]`, `quote-style = "double"`
  - Pytest: `asyncio_mode = "auto"`
- **CREATE**: `src/agent_youtube_summary/__init__.py` — Package docstring only
- **CREATE**: `src/agent_youtube_summary/config.py` — Load `DB_PATH`, `OPENAI_API_KEY` from env
  - **PATTERN**: Mirror `Utils-YouTube/src/utils_youtube/config.py`
  - `DB_PATH` default: `../../data/artimesone.db`
  - `OPENAI_API_KEY` default: empty string
  - `ROLLUP_OUTPUT_DIR` default: `../../data/agent-youtube-summary`
  - `SETTINGS_PATH` default: `settings.json` (resolved relative to project root)
  - `PROMPTS_DIR` default: `prompts/` (resolved relative to project root)
- **CREATE**: `.env.example` documenting all env vars (YOUTUBE_API_KEY, APIFY_API_KEY, OPENAI_API_KEY, DB_PATH)
- **CREATE**: `tests/__init__.py` — Empty
- **CREATE**: `tests/conftest.py` — Placeholder with basic fixtures
- **VALIDATE**: `cd Agent-YouTube-Summary && uv sync && uv run python -c "import agent_youtube_summary; print('OK')"`

### Task 2: Settings Schema and Loader

Implement the settings layer — the JSON schema for Dashboard rendering and the Python loader that validates `settings.json` at runtime.

- **CREATE**: `settings.schema.json` — Copy schema structure from PRD (channels array, schedule, channelCooldownDays, maxVideosPerChannel, maxTranscriptDurationMinutes, summaryModel). **OVERRIDE**: Change `summaryModel` default from the PRD's Claude model to `"gpt-4o-mini"` (OpenAI).
- **CREATE**: `settings.json` — Default values with two example channels (3Blue1Brown, Fireship) as specified in PRD. Set `summaryModel` to `"gpt-4o-mini"`.
- **CREATE**: `src/agent_youtube_summary/settings.py`:
  - Define `ChannelConfig` Pydantic model: `channel_id: str`, `name: str`
  - Define `SummarySettings` Pydantic model with all settings fields and defaults matching schema
  - `async def load_settings() -> SummarySettings` — Read `settings.json` from `SETTINGS_PATH`, parse with Pydantic, return model. Log warning and return defaults if file is missing or invalid.
  - **PATTERN**: Use `model_config` not legacy `Config` class
  - **IMPORTS**: `pydantic.BaseModel`, `pydantic.Field`, `json`, `pathlib.Path`, `logging`
  - **GOTCHA**: `settings.json` uses camelCase keys (matching the JSON schema). Use Pydantic `alias` or `model_config = ConfigDict(populate_by_name=True, alias_generator=...)` to map camelCase JSON to snake_case Python. Alternatively, keep the Pydantic field names in camelCase via aliases. Recommended: use `Field(alias="channelId")` for each field.
- **CREATE**: `tests/test_settings.py` — Test loading valid settings, missing file fallback, invalid JSON handling
- **VALIDATE**: `uv run pytest tests/test_settings.py -v`

### Task 3: Database Layer

Implement the SQLite data layer with all three tables, async operations, and the query functions needed by the pipeline.

- **CREATE**: `src/agent_youtube_summary/db.py`:
  - `async def get_connection() -> aiosqlite.Connection` — Open connection to `DB_PATH`, enable WAL mode (`PRAGMA journal_mode=WAL`), return connection
  - `async def ensure_tables(conn: aiosqlite.Connection) -> None` — Create all three tables if not exists:
    - `agent_youtube_summary_channels` (channel_id TEXT PK, name TEXT, last_checked_at TIMESTAMP, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    - `agent_youtube_summary_items` (video_id TEXT PK, channel_id TEXT, channel_name TEXT, title TEXT, description TEXT, published_at TIMESTAMP, duration TEXT, view_count INT, like_count INT, comment_count INT, thumbnail_url TEXT, transcript TEXT, collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status TEXT DEFAULT 'collected')
    - `agent_youtube_summary_summaries` (video_id TEXT PK, summary TEXT, topics TEXT, key_points TEXT, model_used TEXT, prompt_version TEXT, summarized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
  - `async def sync_channels(conn, channels: list[ChannelConfig]) -> None` — Insert channels from settings that don't exist. Do NOT delete removed channels (just ignore them in queries).
  - `async def get_next_channel(conn, channels: list[ChannelConfig], cooldown_days: int) -> str | None` — Return channel_id of the next eligible channel: must be in settings list, prefer NULL `last_checked_at`, then oldest `last_checked_at`, skip if checked within `cooldown_days`. Return None if no channel is due.
  - `async def video_exists_with_transcript(conn, video_id: str) -> bool` — Check if video exists and has non-null transcript
  - `async def upsert_video(conn, video_id, channel_id, channel_name, title, description, published_at, duration, view_count, like_count, comment_count, thumbnail_url, transcript, status) -> None` — INSERT OR REPLACE into items table
  - `async def update_channel_checked(conn, channel_id: str) -> None` — Set `last_checked_at` to now
  - `async def get_collected_items(conn) -> list[dict]` — Return items where `status = 'collected'` and `transcript IS NOT NULL`
  - `async def insert_summary(conn, video_id, summary, topics, key_points, model_used, prompt_version) -> None` — Insert into summaries table. `topics` and `key_points` stored as JSON strings.
  - `async def update_item_status(conn, video_id: str, status: str) -> None` — Update status on items table
  - `async def get_todays_summaries(conn) -> list[dict]` — Join summaries with items where `summarized_at` is today, grouped by channel for rollup
  - **PATTERN**: All functions take a `conn` parameter. The caller manages the connection lifecycle.
  - **GOTCHA**: Use parameterized queries everywhere — never f-string SQL. Use `aiosqlite.Connection.execute()` with `?` placeholders.
  - **GOTCHA**: `topics` and `key_points` in summaries table are JSON strings (`json.dumps(list)`). Deserialize on read with `json.loads()`.
- **CREATE**: `tests/test_db.py` — Use in-memory SQLite (`:memory:`) for fast isolated tests. Test: table creation, channel sync, next channel selection with cooldown, upsert deduplication, status transitions, today's summaries query.
- **VALIDATE**: `uv run pytest tests/test_db.py -v`

### Task 4: Stage 1 — Collection Pipeline

Implement the full Stage 1 pipeline that selects a channel, fetches videos, collects transcripts, and stores everything in SQLite.

- **CREATE**: `src/agent_youtube_summary/stage_collect.py`:
  - `async def run_collect(settings: SummarySettings) -> int` — Returns count of videos collected. Full flow:
    1. Open DB connection, ensure tables
    2. Sync channels from settings
    3. Get next eligible channel (returns None → log and return 0)
    4. Call `fetch_recent_video_ids(channel_id, max_results=settings.max_videos_per_channel)` from utils-youtube
    5. Call `fetch_video_details(video_ids)` from utils-youtube
    6. For each video: check if it already exists with transcript in DB. If new or missing transcript, and `duration_seconds(video.duration) < settings.max_transcript_duration_minutes * 60`: add to transcript batch
    7. Call `fetch_transcripts(need_transcript_ids)` from utils-youtube (single batch)
    8. For each video from step 5: upsert into items table with transcript from step 7 (or None). Set status = `'collected'` if transcript available, `'skipped'` if not.
    9. Update `last_checked_at` on the channel
    10. Return count of upserted videos
  - **IMPORTS**: `from utils_youtube import fetch_recent_video_ids, fetch_video_details, fetch_transcripts, duration_seconds`
  - **GOTCHA**: `fetch_transcripts` returns `dict[str, str]` mapping video_id to transcript text. Videos not in the dict have no transcript.
  - **GOTCHA**: `VideoMetadata.duration` is an ISO 8601 string like "PT12M30S". Use `duration_seconds()` to convert to seconds for comparison.
  - **GOTCHA**: `fetch_video_details` returns `list[VideoMetadata]`. Map model fields to DB columns: `video.video_id`, `video.channel_id`, `video.channel_name`, `video.title`, `video.description`, `video.published_at` (datetime|None — store as ISO string), `video.duration`, `video.view_count`, `video.like_count`, `video.comment_count`, `video.thumbnail_url`.
- **CREATE**: `tests/test_stage_collect.py` — Mock all utils-youtube calls and DB. Test: full happy path, no eligible channel exits early, duration filtering works, existing videos with transcripts are skipped, transcript fetch failure marks as skipped.
- **VALIDATE**: `uv run pytest tests/test_stage_collect.py -v`

### Task 5: Prompt Template

Create the LLM prompt template used by Stage 2.

- **CREATE**: `prompts/summarize_video.md` — Exact template from PRD:
  ```
  Summarize the following YouTube video.

  **Title:** {{title}}
  **Channel:** {{channel_name}}
  **Description:** {{description}}

  **Transcript:**
  {{transcript}}

  Respond in the following JSON format:
  {
    "summary": "A concise 2-3 sentence summary of the video.",
    "topics": ["topic1", "topic2"],
    "key_points": ["point 1", "point 2", "point 3"]
  }
  ```
- **GOTCHA**: Template uses `{{variable}}` syntax. Use Python `str.replace()` or a simple template function — no need for Jinja2. Keep the replacement simple and explicit.
- **VALIDATE**: File exists and is valid markdown.

### Task 6: Stage 2 — Summarization Pipeline

Implement the LLM-powered summarization stage.

- **CREATE**: `src/agent_youtube_summary/stage_summarize.py`:
  - `PROMPT_VERSION = "v1"` — Track which prompt version produced each summary. Increment on prompt changes.
  - `_MAX_TRANSCRIPT_CHARS = 100_000` — Truncation limit for transcript before sending to LLM. Full transcript is preserved in DB.
  - `async def _load_prompt_template() -> str` — Read `prompts/summarize_video.md` from `PROMPTS_DIR`. Cache in module-level variable after first read.
  - `async def _render_prompt(template: str, title: str, channel_name: str, description: str, transcript: str) -> str` — Replace `{{title}}`, `{{channel_name}}`, `{{description}}`, `{{transcript}}` in template. Truncate transcript to `_MAX_TRANSCRIPT_CHARS` before injection.
  - `async def _call_llm(prompt: str, model: str) -> dict | None` — Call OpenAI chat completions API:
    ```python
    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    response = await client.chat.completions.create(
        model=model,
        max_tokens=1024,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes YouTube videos. Always respond with valid JSON."},
            {"role": "user", "content": prompt},
        ],
    )
    ```
    Parse `response.choices[0].message.content` as JSON. Return dict with keys `summary`, `topics`, `key_points`. Return None if parsing fails.
  - `async def run_summarize(settings: SummarySettings) -> int` — Returns count of videos summarized. Full flow:
    1. Open DB connection
    2. Load prompt template
    3. Get all collected items (status='collected', transcript IS NOT NULL)
    4. For each item:
       a. Render prompt with item data
       b. Call LLM with `settings.summary_model`
       c. On success: insert summary, update item status → 'summarized'
       d. On failure: update item status → 'failed', log error
    5. Return count of successfully summarized videos
  - **IMPORTS**: `openai`, `json`, `logging`
  - **GOTCHA**: LLM response may not be valid JSON even with `response_format={"type": "json_object"}`. Wrap `json.loads()` in try/except. If parsing fails, mark as `'failed'`.
  - **GOTCHA**: The OpenAI SDK response is `response.choices[0].message.content` — a string. Parse it with `json.loads()`.
  - **GOTCHA**: `topics` and `key_points` from LLM response are lists. Store as `json.dumps(list)` in the DB.
- **CREATE**: `tests/test_stage_summarize.py` — Mock the OpenAI client. Test: happy path produces correct summary record, invalid JSON marks as failed, empty collected items returns 0, prompt template loading.
- **VALIDATE**: `uv run pytest tests/test_stage_summarize.py -v`

### Task 7: Rollup Generator

Implement the deterministic markdown rollup that assembles today's summaries into a daily digest file.

- **CREATE**: `src/agent_youtube_summary/rollup.py`:
  - `async def run_rollup() -> str | None` — Returns the file path of the generated rollup, or None if no summaries today. Full flow:
    1. Open DB connection
    2. Query today's summaries joined with items, grouped by channel
    3. If no summaries → log and return None
    4. Render markdown following the exact format from the PRD:
       ```markdown
       # YouTube Summary — YYYY-MM-DD

       ## Channel Name

       ### Video Title
       ![thumbnail](url)
       - **Topics:** topic1, topic2
       - **Key Points:**
         - point 1
         - point 2
       - **Summary:** summary text
       - [Watch](https://youtube.com/watch?v=VIDEO_ID) | duration | views

       ---
       ```
    5. Create output directory if needed (`ROLLUP_OUTPUT_DIR`)
    6. Write to `{ROLLUP_OUTPUT_DIR}/YYYY-MM-DD.md`
    7. Return file path
  - **GOTCHA**: `topics` and `key_points` are JSON strings in the DB — `json.loads()` them before rendering.
  - **GOTCHA**: Duration is stored as ISO 8601 string. Convert to human-readable format (e.g., "18 min") using `duration_seconds()` and dividing.
  - **GOTCHA**: View count formatting — use locale-aware formatting or simple comma separation.
- **CREATE**: `tests/test_rollup.py` — Use in-memory DB with pre-inserted test data. Test: generates correct markdown structure, handles no summaries gracefully, creates output directory, formats duration and view counts correctly.
- **VALIDATE**: `uv run pytest tests/test_rollup.py -v`

### Task 8: Dashboard Contract Files

Create the ArtimesOne contract files: registry entry and widget declarations.

- **CREATE**: `registry.json` — Exact content from PRD:
  ```json
  {
    "id": "agent-youtube-summary",
    "name": "YouTube Summary",
    "category": "Agent",
    "icon": "youtube",
    "route": "/agent-youtube-summary"
  }
  ```
- **CREATE**: `widgets.schema.json` — Exact content from PRD with all five widgets:
  1. `total_videos` (count) — total items
  2. `new_since_last_visit` (count) — summaries since `:last_visit`
  3. `last_run` (date) — max `collected_at`
  4. `recent_videos` (list) — 5 most recent items
  5. `channels_tracked` (count) — channel count
- **VALIDATE**: Both files are valid JSON: `uv run python -c "import json; json.load(open('registry.json')); json.load(open('widgets.schema.json')); print('OK')"`

### Task 9: Pipeline Orchestrator

Create the top-level entry point that runs all three stages sequentially.

- **CREATE**: `src/agent_youtube_summary/pipeline.py`:
  - `async def run_pipeline() -> None` — Main entry point:
    1. Load settings
    2. Run Stage 1 (collect) — log count
    3. Run Stage 2 (summarize) — log count
    4. Run rollup — log file path or "no summaries"
    5. Log total pipeline duration
  - Add `if __name__ == "__main__":` block with `asyncio.run(run_pipeline())` for direct execution
  - Configure logging at the top of `__main__` block: `logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")`
- **CREATE**: `tests/test_pipeline.py` — Integration test mocking all three stages. Test: stages run in order, stage failure doesn't block subsequent stages (collect fail → summarize still runs on existing data → rollup still runs).
- **VALIDATE**: `uv run pytest tests/test_pipeline.py -v`

### Task 10: Edge Case Hardening

Add robustness for all edge cases identified in the PRD.

- **UPDATE**: `src/agent_youtube_summary/stage_collect.py`:
  - Handle empty channel list in settings (log warning, return 0)
  - Handle `fetch_recent_video_ids` returning empty list
  - Handle `fetch_video_details` returning empty list
  - Handle `fetch_transcripts` returning empty dict
- **UPDATE**: `src/agent_youtube_summary/stage_summarize.py`:
  - Handle LLM timeout (wrap in try/except for `openai.APITimeoutError`)
  - Handle rate limit errors (`openai.RateLimitError`) — log and mark as failed
  - Handle malformed JSON responses
- **UPDATE**: `src/agent_youtube_summary/rollup.py`:
  - Handle items with missing optional fields (no thumbnail, no view_count)
  - Handle empty summaries query gracefully
- **ADD**: Additional test cases for each edge case
- **VALIDATE**: `uv run pytest tests/ -v`

### Task 11: Linting, Formatting, and Final Validation

Ensure all code passes quality checks and the full test suite.

- **VALIDATE**: `uv run ruff check src/ tests/` — Must pass with 0 errors
- **VALIDATE**: `uv run ruff format --check src/ tests/` — Must pass
- **VALIDATE**: `uv run pytest tests/ -v` — All tests must pass
- **VALIDATE**: `uv run python -m agent_youtube_summary.pipeline` — Dry run (will exit early with no API keys, but should not crash)
- **FIX**: Any issues found by the above commands

---

## TESTING STRATEGY

### Unit Tests

Each module gets its own test file. All external I/O is mocked:
- **Database**: Use `aiosqlite` with `:memory:` database for isolated, fast tests
- **utils-youtube calls**: Mock at the function level using `monkeypatch` or `unittest.mock.AsyncMock`
- **OpenAI SDK**: Mock the `AsyncOpenAI` client and its `chat.completions.create` method
- **File I/O**: Use `tmp_path` fixture for rollup output and prompt template reading

### Integration Tests

`test_pipeline.py` tests the full pipeline flow with all external calls mocked. Verifies:
- Stages execute in correct order
- Data flows correctly between stages (collect writes to DB → summarize reads from DB → rollup reads from DB)
- Pipeline handles partial failures gracefully

### Edge Cases

- Empty channel list in settings
- No eligible channel (all within cooldown)
- Channel with zero videos
- All videos exceed duration limit
- All transcript fetches fail (empty dict from `fetch_transcripts`)
- Video already exists with transcript (skip behavior)
- LLM returns invalid JSON
- LLM timeout or rate limit
- No summaries to roll up today
- Missing optional fields (no thumbnail, no view_count, no description)

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
# Lint (must pass with 0 errors)
cd Agent-YouTube-Summary && uv run ruff check src/ tests/

# Format check
cd Agent-YouTube-Summary && uv run ruff format --check src/ tests/
```

**Expected**: All commands pass with exit code 0

### Level 2: Unit Tests

```bash
cd Agent-YouTube-Summary && uv run pytest tests/ -v
```

**Expected**: All tests pass. Target 80%+ coverage on src/ modules.

### Level 3: Integration Tests

```bash
cd Agent-YouTube-Summary && uv run pytest tests/test_pipeline.py -v
```

**Expected**: Pipeline integration tests pass with mocked external services.

### Level 4: Manual Validation

```bash
# Verify package imports cleanly
cd Agent-YouTube-Summary && uv run python -c "from agent_youtube_summary.pipeline import run_pipeline; print('OK')"

# Verify settings load
cd Agent-YouTube-Summary && uv run python -c "
import asyncio
from agent_youtube_summary.settings import load_settings
s = asyncio.run(load_settings())
print(f'Channels: {len(s.channels)}, Model: {s.summary_model}')
"

# Verify contract files are valid JSON
cd Agent-YouTube-Summary && uv run python -c "
import json
json.load(open('registry.json'))
json.load(open('settings.schema.json'))
json.load(open('settings.json'))
json.load(open('widgets.schema.json'))
print('All contract files valid')
"

# Verify DB tables can be created
cd Agent-YouTube-Summary && uv run python -c "
import asyncio, aiosqlite
from agent_youtube_summary.db import ensure_tables
async def check():
    async with aiosqlite.connect(':memory:') as conn:
        await ensure_tables(conn)
        cursor = await conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
        tables = [row[0] for row in await cursor.fetchall()]
        print(f'Tables: {tables}')
asyncio.run(check())
"
```

### Level 5: Dry Run

```bash
# Pipeline dry run (will exit early without API keys but should not crash)
cd Agent-YouTube-Summary && uv run python -m agent_youtube_summary.pipeline
```

**Expected**: Logs "no eligible channel" or similar and exits cleanly without tracebacks.

---

## ACCEPTANCE CRITERIA

- [ ] Pipeline runs end-to-end: collect → summarize → rollup from a single entry point
- [ ] Stage 1 fetches videos from utils-youtube and stores in SQLite
- [ ] Channel priority queue works: NULL last_checked first, then oldest
- [ ] Cooldown enforcement: channels checked within N days are skipped
- [ ] Duration filtering: videos over the configured limit are skipped
- [ ] Duplicate handling: upsert on video_id produces no duplicate rows
- [ ] Stage 2 calls configurable LLM model and produces structured summary
- [ ] Failed summarizations are marked 'failed' and don't block other videos
- [ ] Rollup generates correct markdown grouped by channel
- [ ] All ArtimesOne contract files are present and valid (registry, settings schema, widgets)
- [ ] Settings changes take effect on next pipeline run
- [ ] All validation commands pass with zero errors
- [ ] Unit test coverage meets 80%+ requirement
- [ ] Code follows CLAUDE.md conventions (async, type hints, logging, docstrings)
- [ ] No regressions in existing functionality

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order (1-11)
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully:
  - [ ] Level 1: ruff check, ruff format --check
  - [ ] Level 2: pytest (unit tests)
  - [ ] Level 3: pytest (integration tests)
  - [ ] Level 4: Manual validation
  - [ ] Level 5: Dry run
- [ ] Full test suite passes (unit + integration)
- [ ] No linting errors
- [ ] No formatting errors
- [ ] All acceptance criteria met
- [ ] Code reviewed for quality and maintainability

---

## EXECUTION STRATEGY

**Recommended approach**: Milestones

**Rationale**: This feature has 11 tasks with natural layering: the data layer (Tasks 1-3) must exist before the pipeline stages (Tasks 4-7) can be built, and the pipeline must work before contract files and hardening (Tasks 8-11) make sense. Tasks within each milestone are tightly coupled (e.g., db.py and settings.py are both needed by stage_collect.py), but milestones are loosely coupled and each produces a testable checkpoint. The high complexity (new project, 7 source modules, 3 pipeline stages, 4 contract files) means a single-pass approach is too risky, while task-by-task is unnecessarily granular given the tight coupling within layers.

### Milestones

**Milestone 1: Foundation** (Tasks 1–3)
- Project scaffolding, configuration, settings loader, and full database layer
- **Validation checkpoint**: `uv sync` succeeds, settings load from JSON, all 3 SQLite tables create correctly, channel sync and next-channel queries work in tests

**Milestone 2: Pipeline Core** (Tasks 4–6)
- Stage 1 collection, prompt template, and Stage 2 summarization
- **Validation checkpoint**: Collection pipeline fetches/stores videos with mocked utils-youtube, summarization produces structured output with mocked LLM, all pipeline tests pass

**Milestone 3: Output and Contract** (Tasks 7–8)
- Rollup markdown generator and all ArtimesOne contract files
- **Validation checkpoint**: Rollup generates correct markdown from test data, all contract JSON files are valid and match PRD specs

**Milestone 4: Integration and Hardening** (Tasks 9–11)
- Pipeline orchestrator, edge case handling, and final quality pass
- **Validation checkpoint**: Full pipeline runs end-to-end (mocked), all edge cases tested, ruff check/format pass, full test suite green, dry run exits cleanly

---

## NOTES

- **utils-youtube is fully implemented and tested** — no changes needed. Import directly.
- **Path dependency**: `utils-youtube` should be a path dependency in `pyproject.toml` since both projects live in the same workspace. Use `{path = "../Utils-YouTube", editable = true}`.
- **SQLite WAL mode**: Must be enabled on every connection for concurrent read support. The architecture doc mandates this.
- **Transcript truncation**: The PRD explicitly states full transcripts are preserved in the DB. Truncation ONLY happens when rendering the LLM prompt in Stage 2. This is a core principle — do not truncate on storage.
- **camelCase in JSON, snake_case in Python**: The `settings.schema.json` and `settings.json` use camelCase (standard for JSON Schema). The Python settings model should use Pydantic aliases to bridge the naming gap.
- **No automatic retry**: The PRD explicitly states failed summarizations require manual reset. Do not implement automatic retry logic.
- **One channel per run**: The PRD explicitly states each pipeline invocation processes one channel. Do not process multiple channels.
- **OpenAI SDK**: Use `openai.AsyncOpenAI` for async LLM calls. The default model should be an OpenAI model (e.g., `gpt-4o-mini`) from settings. Use `response_format={"type": "json_object"}` to encourage valid JSON output.
- **File paths**: The agent will be run from its own directory (`Agent-YouTube-Summary/`). Config paths like `DB_PATH`, `SETTINGS_PATH`, and `PROMPTS_DIR` should be resolved relative to the project root or use absolute paths from env vars.
