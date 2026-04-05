# Feature: Align Agent-YouTube-Summary with ArtimesOne Shared Platform

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Bring Agent-YouTube-Summary into full compliance with the ArtimesOne shared platform specification (`Docs/artimesone-shared-platform.md`). The agent's pipeline, database layer, and tests are already solid. What's missing is the web UI layer (FastAPI app, settings page, output viewer) and several contract file / config corrections. This work also creates the minimal shared infrastructure (`shared/css/`, `shared/templates/`) that doesn't exist yet but is required for any agent to render its web UI.

## User Story

As a platform operator
I want Agent-YouTube-Summary to run as a contract-compliant web application with a settings page and rollup viewer
So that it integrates with the ArtimesOne sidebar, renders the shared visual identity, and I can configure it without editing JSON files manually.

## Problem Statement

The agent implements its pipeline correctly but has no web UI. The platform's shared infrastructure (CSS, base template) doesn't exist yet. Several contract files have incorrect fields (registry.json uses `route` instead of `url`). The config layer is missing shared environment variables required by the platform spec. Without these, the agent cannot participate in the ArtimesOne ecosystem as defined.

## Solution Statement

1. Create the minimal shared infrastructure (`shared/css/artimesone.css`, `shared/templates/base.html`) at the workspace root.
2. Fix contract files (`registry.json`, `widgets.schema.json`).
3. Update config/env to include all shared platform variables.
4. Build a FastAPI web app with settings page and rollup viewer, extending the shared template.
5. Add web-layer dependencies (FastAPI, uvicorn, Jinja2, httpx for testing).
6. Add tests for the new web layer.

## Feature Metadata

**Feature Type**: Enhancement
**Estimated Complexity**: Medium-High
**Primary Systems Affected**: Agent-YouTube-Summary (web layer, config), shared/ (new), contract files
**Dependencies**: FastAPI 0.115+, Uvicorn 0.34+, Jinja2 3.x, httpx 0.28+ (test client)

---

## CONTEXT REFERENCES

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `Agent-YouTube-Summary/src/agent_youtube_summary/config.py` (lines 1-37) — Current config module. Must be extended with WORKSPACE_DIR, SHARED_DIR, DATA_DIR, HOST, PORT.
- `Agent-YouTube-Summary/src/agent_youtube_summary/settings.py` (lines 1-61) — Pydantic settings model with camelCase aliases. The settings page will read/write through this.
- `Agent-YouTube-Summary/src/agent_youtube_summary/db.py` (lines 1-290) — Database layer. The web app will use `get_connection()` and query patterns from here.
- `Agent-YouTube-Summary/src/agent_youtube_summary/rollup.py` (lines 85-111) — `run_rollup()` writes to `ROLLUP_OUTPUT_DIR`. The output viewer will read files from this directory.
- `Agent-YouTube-Summary/src/agent_youtube_summary/pipeline.py` (lines 1-58) — Standalone entry point. No changes needed but understanding the structure helps.
- `Agent-YouTube-Summary/registry.json` (lines 1-7) — Has wrong field `route`, must change to `url`.
- `Agent-YouTube-Summary/widgets.schema.json` (lines 1-35) — Widget `new_since_last_visit` uses unresolvable `:last_visit` bind parameter.
- `Agent-YouTube-Summary/settings.schema.json` (lines 1-61) — JSON Schema for settings form rendering. Read this to understand how the settings page form should be structured.
- `Agent-YouTube-Summary/settings.json` (lines 1-11) — Current values. The settings page reads and writes this file.
- `Agent-YouTube-Summary/pyproject.toml` (lines 1-43) — Dependencies. Must add FastAPI, uvicorn, Jinja2, httpx (dev).
- `Agent-YouTube-Summary/.env.example` (lines 1-11) — Must add shared platform variables.
- `Agent-YouTube-Summary/tests/conftest.py` (lines 1-82) — Test fixture patterns to follow.
- `Docs/artimesone-shared-platform.md` (full file) — The authoritative spec. Every decision should trace back here.
- `Docs/PRD-artimesone.md` (lines 70-77, 320-350) — Agent web UI requirements and settings page spec.

### New Files to Create

**Shared infrastructure (workspace root):**
- `shared/css/artimesone.css` — Minimal platform stylesheet with CSS custom properties, sidebar layout, component styles
- `shared/templates/base.html` — Jinja2 base layout with sidebar and content block

**Agent web layer:**
- `Agent-YouTube-Summary/src/agent_youtube_summary/app.py` — FastAPI app factory with static mounts and Jinja2 setup
- `Agent-YouTube-Summary/src/agent_youtube_summary/discovery.py` — Workspace scanner for `Agent-*/registry.json` files
- `Agent-YouTube-Summary/src/agent_youtube_summary/routes/__init__.py` — Routes package
- `Agent-YouTube-Summary/src/agent_youtube_summary/routes/settings_page.py` — Settings form page (GET renders form, POST saves)
- `Agent-YouTube-Summary/src/agent_youtube_summary/routes/rollups.py` — Rollup output viewer (list + detail pages)
- `Agent-YouTube-Summary/templates/settings.html` — Agent-specific settings page template
- `Agent-YouTube-Summary/templates/rollups.html` — Rollup list template
- `Agent-YouTube-Summary/templates/rollup_detail.html` — Single rollup view template

**Tests:**
- `Agent-YouTube-Summary/tests/test_app.py` — FastAPI app and route tests
- `Agent-YouTube-Summary/tests/test_discovery.py` — Workspace scanner tests

### Relevant Documentation — READ BEFORE IMPLEMENTING

- FastAPI Static Files: https://fastapi.tiangolo.com/tutorial/static-files/
  - Specific: mounting static directories for shared CSS
- FastAPI with Jinja2 Templates: https://fastapi.tiangolo.com/advanced/templates/
  - Specific: `Jinja2Templates(directory=...)` with multiple directories
- FastAPI TestClient with httpx: https://fastapi.tiangolo.com/tutorial/testing/
  - Specific: async test patterns with `httpx.AsyncClient`
- Jinja2 Template Inheritance: https://jinja.palletsprojects.com/en/3.1.x/templates/#template-inheritance
  - Specific: `{% extends "base.html" %}` and `{% block content %}`

### Patterns to Follow

**Naming Conventions:**
- Modules: `snake_case` (e.g., `settings_page.py`, `discovery.py`)
- Classes: `PascalCase` (e.g., `ChannelConfig`)
- Functions: `snake_case` (e.g., `discover_agents()`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `WORKSPACE_DIR`)
- Config variables: loaded from env in `config.py`, imported by other modules

**Error Handling (from existing code):**
```python
# Pattern from settings.py:44-60 — graceful fallback
try:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    return SummarySettings.model_validate(data)
except (json.JSONDecodeError, ValueError) as exc:
    logger.warning("Invalid settings file at %s: %s — using defaults", path, exc)
    return SummarySettings()
```

**Logging Pattern (from every module):**
```python
import logging
logger = logging.getLogger(__name__)
```

**Database Connection Pattern (from db.py:21-26):**
```python
async def get_connection() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(DB_PATH)
    await conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = aiosqlite.Row
    return conn
```

**Async Test Pattern (from existing tests):**
```python
# All tests are async, pytest-asyncio with asyncio_mode = "auto"
async def test_something():
    result = await some_async_function()
    assert result == expected
```

**Mock Pattern (from test_stage_collect.py):**
```python
with patch("agent_youtube_summary.module.function", new_callable=AsyncMock, return_value=...):
    result = await function_under_test()
```

**Pydantic alias pattern (from settings.py) — camelCase JSON <-> snake_case Python:**
```python
class SummarySettings(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    channel_cooldown_days: int = Field(default=3, alias="channelCooldownDays")
```

---

## IMPLEMENTATION PLAN

### Task 1: Create shared infrastructure — CSS and base template

This task creates the workspace-level `shared/` directory that every app depends on. Nothing else can render until these exist.

- **CREATE** `shared/css/artimesone.css` — Minimal but functional stylesheet:
  - CSS custom properties for colors (`--color-bg`, `--color-sidebar-bg`, `--color-text`, `--color-primary`, `--color-border`, etc.), spacing, typography, border-radii
  - Sidebar layout: fixed-width left sidebar (240px) + fluid content area
  - Sidebar styles: nav links, active state highlighting, category headings, icons
  - Content area: max-width container, padding, heading styles
  - Component styles: cards (for widgets/status), forms (text inputs, number inputs, checkboxes, selects, array groups with add/remove buttons), tables, buttons, status badges
  - Utility: `.sr-only` for accessibility, basic reset
  - Per spec: "desktop-optimized, mobile is not an MVP target"
  - Reference: `Docs/artimesone-shared-platform.md` lines 70-84 and `Docs/PRD-artimesone.md` lines 262-267
- **CREATE** `shared/templates/base.html` — Jinja2 base layout:
  - `<!DOCTYPE html>` with `<html lang="en">`
  - `<head>`: charset, viewport, title block (`{% block title %}ArtimesOne{% endblock %}`), CSS link to `/static/shared/css/artimesone.css`
  - `<body>`: two-column layout — sidebar + main content
  - Sidebar: rendered from `sidebar_agents` template variable (list of dicts with id, name, category, icon, url). Highlight the currently active app using an `active_agent_id` template variable. Group entries by `category`. Links use full URLs.
  - Main content: `{% block content %}{% endblock %}`
  - Optional: `{% block scripts %}{% endblock %}` for page-specific JS
  - Reference: `Docs/artimesone-shared-platform.md` lines 86-143
- **CREATE** `data/` directory — empty, for SQLite database and markdown outputs (created by mkdir, agents create their own subdirs on first run)
- **GOTCHA**: Use relative paths in CSS link (`/static/shared/css/artimesone.css`) — each app mounts this at the same path. The sidebar `url` values are full URLs with ports (e.g., `http://localhost:8001`).
- **GOTCHA**: The `sidebar_agents` variable must be populated by each app independently. The template should iterate over it but not be responsible for building it.
- **VALIDATE**: Verify files exist:
  ```bash
  ls shared/css/artimesone.css shared/templates/base.html
  ```

### Task 2: Fix contract files — registry.json and widgets.schema.json

Quick fixes to bring contract files in line with the spec.

- **UPDATE** `Agent-YouTube-Summary/registry.json`:
  - Remove `"route": "/agent-youtube-summary"`
  - Add `"url": "http://localhost:8001"`
  - Reference: `Docs/artimesone-shared-platform.md` lines 196-219
  - Final file:
    ```json
    {
      "id": "agent-youtube-summary",
      "name": "YouTube Summary",
      "category": "Agent",
      "icon": "youtube",
      "url": "http://localhost:8001"
    }
    ```
- **UPDATE** `Agent-YouTube-Summary/widgets.schema.json`:
  - Change `new_since_last_visit` widget query from `WHERE summarized_at > :last_visit` to a self-contained query: `SELECT COUNT(*) FROM agent_youtube_summary_summaries WHERE summarized_at > datetime('now', '-1 day')`
  - The spec defines no mechanism for the Dashboard to provide bind parameters. The query must be self-contained.
  - Also update `recent_videos` query to match the spec example column selection (current has `i.thumbnail_url` which the spec example doesn't — keep it, it's useful and the spec says "additional columns are fine")
- **VALIDATE**:
  ```bash
  python -c "import json; d=json.load(open('Agent-YouTube-Summary/registry.json')); assert 'url' in d and 'route' not in d; print('registry.json OK')"
  python -c "import json; d=json.load(open('Agent-YouTube-Summary/widgets.schema.json')); assert ':last_visit' not in str(d); print('widgets.schema.json OK')"
  ```

### Task 3: Update config and environment variables

Add all shared platform variables to the config layer.

- **UPDATE** `Agent-YouTube-Summary/.env.example` — Add shared platform variables:
  ```
  # Shared platform paths
  WORKSPACE_DIR=..
  SHARED_DIR=../shared
  DB_PATH=../data/artimesone.db
  DATA_DIR=../data

  # Web server
  HOST=127.0.0.1
  PORT=8001

  # Agent-specific secrets (not part of contract)
  OPENAI_API_KEY=

  # YouTube and Apify keys are handled by utils-youtube — see its .env.example
  ```
  - Remove `ROLLUP_OUTPUT_DIR` (will be derived from `DATA_DIR`)
- **UPDATE** `Agent-YouTube-Summary/src/agent_youtube_summary/config.py`:
  - Add new environment variable constants: `WORKSPACE_DIR`, `SHARED_DIR`, `DATA_DIR`, `HOST`, `PORT`
  - Derive `ROLLUP_OUTPUT_DIR` from `DATA_DIR`: `os.path.join(DATA_DIR, "agent-youtube-summary")`
  - Keep `ROLLUP_OUTPUT_DIR` as an exported constant (rollup.py imports it) but compute it from `DATA_DIR`
  - Keep existing variables: `DB_PATH`, `OPENAI_API_KEY`, `SETTINGS_PATH`, `PROMPTS_DIR`
  - Reference: `Docs/artimesone-shared-platform.md` lines 500-556
  - **PATTERN**: Follow existing config.py style — module-level constants with docstrings, `os.environ.get()` with defaults
- **GOTCHA**: The `_PROJECT_ROOT` derivation (`Path(__file__).resolve().parent.parent.parent`) must remain correct. Verify the directory math: `__file__` is `src/agent_youtube_summary/config.py`, so `.parent.parent.parent` is the project root. This is correct.
- **GOTCHA**: `ROLLUP_OUTPUT_DIR` was previously a standalone env var. After this change it derives from `DATA_DIR`. If anyone has `ROLLUP_OUTPUT_DIR` in their `.env`, it will be silently ignored. This is acceptable — the `.env.example` is being updated to remove it.
- **VALIDATE**:
  ```bash
  cd Agent-YouTube-Summary && uv run python -c "from agent_youtube_summary.config import WORKSPACE_DIR, SHARED_DIR, DATA_DIR, HOST, PORT, ROLLUP_OUTPUT_DIR; print('All config vars importable')"
  ```

### Task 4: Add web dependencies to pyproject.toml

Add FastAPI, uvicorn, Jinja2 to core deps. Add httpx to dev deps for test client.

- **UPDATE** `Agent-YouTube-Summary/pyproject.toml`:
  - Add to `dependencies`:
    - `"fastapi>=0.115,<1.0"`
    - `"uvicorn>=0.34,<1.0"`
    - `"jinja2>=3.1,<4.0"`
  - Add to `[project.optional-dependencies] dev`:
    - `"httpx>=0.28,<1.0"` (FastAPI test client)
  - Reference: `Docs/PRD-artimesone.md` lines 377-408 for version requirements
- **VALIDATE**:
  ```bash
  cd Agent-YouTube-Summary && uv sync && uv run python -c "import fastapi; import uvicorn; import jinja2; print('Web deps OK')"
  ```

### Task 5: Implement discovery module

Create the workspace scanner that reads `Agent-*/registry.json` files for sidebar construction. This is used by the FastAPI app to populate the sidebar on each request.

- **CREATE** `Agent-YouTube-Summary/src/agent_youtube_summary/discovery.py`:
  - `def discover_agents(workspace_dir: str) -> list[dict]` — Synchronous (file I/O only, fast enough for per-request use):
    1. Scan `workspace_dir` for directories matching `Agent-*/`
    2. For each, check for `registry.json`
    3. Read and parse JSON
    4. Return list of dicts: `[{"id": "...", "name": "...", "category": "...", "icon": "...", "url": "..."}, ...]`
    5. Add Dashboard entry at the beginning: `{"id": "artimesone", "name": "Dashboard", "category": "Platform", "icon": "home", "url": "http://localhost:8000"}`
    6. Sort: Platform category first, then Agents alphabetically by name
    7. Log warnings for malformed registry files, skip them
  - Reference: `Docs/artimesone-shared-platform.md` lines 116-143 (sidebar data structure) and lines 448-478 (discovery mechanism)
  - **PATTERN**: Follow existing module pattern — module docstring, `import logging`, `logger = logging.getLogger(__name__)`, type hints on all signatures
  - **GOTCHA**: Use `pathlib.Path` for cross-platform path handling. The `Agent-*/` glob must work on Windows. Use `Path(workspace_dir).glob("Agent-*")` which returns directories and files — filter to directories only with `.is_dir()`.
  - **GOTCHA**: The Dashboard URL port should come from environment or be a sensible default (8000). For MVP, hardcoding `http://localhost:8000` is fine — it matches the spec.
- **VALIDATE**:
  ```bash
  cd Agent-YouTube-Summary && uv run python -c "from agent_youtube_summary.discovery import discover_agents; print(discover_agents('..'))"
  ```

### Task 6: Build FastAPI application

Create the FastAPI app factory that wires everything together: static mounts, Jinja2 templates, routes, sidebar population.

- **CREATE** `Agent-YouTube-Summary/src/agent_youtube_summary/app.py`:
  - Module docstring: "FastAPI web application for the YouTube Summary agent."
  - Import `FastAPI`, `StaticFiles`, `Jinja2Templates`, `Request` from FastAPI/Starlette
  - Import config values: `SHARED_DIR`, `WORKSPACE_DIR`, `HOST`, `PORT`
  - Import `discover_agents` from `discovery.py`
  - `AGENT_ID = "agent-youtube-summary"` — for sidebar active highlighting
  - Create `app = FastAPI(title="YouTube Summary")` instance
  - Mount shared static files: `app.mount("/static/shared", StaticFiles(directory=os.path.join(SHARED_DIR, "css")), name="shared-css")` — but actually mount the full shared dir to match the CSS path in base.html. The CSS link in base.html will be `/static/shared/css/artimesone.css`, so mount SHARED_DIR at `/static/shared`:
    ```python
    app.mount("/static/shared", StaticFiles(directory=SHARED_DIR), name="shared")
    ```
  - Set up Jinja2Templates with two directories (agent-specific first, shared second):
    ```python
    _project_root = Path(__file__).resolve().parent.parent.parent
    templates = Jinja2Templates(directory=[
        str(_project_root / "templates"),
        os.path.join(SHARED_DIR, "templates"),
    ])
    ```
  - Create a helper to build template context with sidebar data:
    ```python
    def _base_context(request: Request) -> dict:
        agents = discover_agents(WORKSPACE_DIR)
        return {
            "request": request,
            "sidebar_agents": agents,
            "active_agent_id": AGENT_ID,
        }
    ```
  - Include route routers from `routes/` subpackage
  - Add a `__main__`-style runner at bottom or a separate `__main__.py`:
    ```python
    if __name__ == "__main__":
        import uvicorn
        uvicorn.run("agent_youtube_summary.app:app", host=HOST, port=int(PORT), reload=True)
    ```
  - Reference: `Docs/artimesone-shared-platform.md` lines 79-103 for static mount and template setup
  - **PATTERN**: The `templates` and `_base_context` should be importable by route modules. Either export them from `app.py` or use a shared module. Keep it simple — export from `app.py`.
  - **GOTCHA**: Jinja2Templates `directory` parameter accepts a list of directories. Templates are searched in order — agent-specific first, shared second. This is how `{% extends "base.html" %}` resolves to `shared/templates/base.html`.
  - **GOTCHA**: `StaticFiles` requires the directory to exist at startup. If `shared/` doesn't exist, the app will crash. Task 1 must be completed first.
- **CREATE** `Agent-YouTube-Summary/src/agent_youtube_summary/routes/__init__.py`:
  - Empty package marker with docstring: "Route handlers for the YouTube Summary web UI."
- **VALIDATE**:
  ```bash
  cd Agent-YouTube-Summary && uv run python -c "from agent_youtube_summary.app import app; print('App created:', app.title)"
  ```

### Task 7: Implement settings page routes

Build the settings page that renders a form from `settings.schema.json` and reads/writes `settings.json`.

- **CREATE** `Agent-YouTube-Summary/src/agent_youtube_summary/routes/settings_page.py`:
  - `router = APIRouter()`
  - `GET /settings` — Renders the settings form:
    1. Load `settings.schema.json` from project root (use `config.SETTINGS_PATH` to derive the schema path — same directory, different filename)
    2. Load current values from `settings.json` via `load_settings()`
    3. Pass schema + values + base context to `settings.html` template
  - `POST /settings` — Saves settings:
    1. Accept JSON body (the form submits via fetch/JS)
    2. Validate against `settings.schema.json` (basic: check required fields, types)
    3. Write to `settings.json` with `json.dump()` using indent=2
    4. Return JSON response `{"status": "ok"}` or `{"status": "error", "message": "..."}`
    5. No page reload — the JS handles success/error feedback
  - Reference: `Docs/PRD-artimesone.md` lines 320-340 for settings page spec
  - **PATTERN**: Follow the existing `load_settings()` pattern from `settings.py:44-60`. For writing, use `Path.write_text()` with `json.dumps(data, indent=2)`.
  - **IMPORTS**: `from agent_youtube_summary.app import templates, _base_context` and `from agent_youtube_summary.settings import load_settings`
  - **GOTCHA**: The settings JSON uses camelCase keys (matching the schema). The Pydantic model uses aliases. When writing settings back, write the raw JSON as-is from the form — don't round-trip through Pydantic (which would convert to snake_case). The form submits camelCase keys matching the schema.
  - **GOTCHA**: The schema path is `{project_root}/settings.schema.json`. Derive from `_PROJECT_ROOT` in config or compute from `SETTINGS_PATH`.
- **CREATE** `Agent-YouTube-Summary/templates/settings.html`:
  - Extends `base.html`
  - Title block: "Settings — YouTube Summary"
  - Content block: settings form
  - The form should be rendered from the schema dynamically using JavaScript:
    - Read the schema JSON (passed as a `<script>` tag or data attribute)
    - Read the current values JSON (same approach)
    - For each property in the schema, render the appropriate input:
      - `string` → `<input type="text">`
      - `integer` → `<input type="number">` with `min`/`max` from schema
      - `boolean` → `<input type="checkbox">`
      - `string` with `enum` → `<select>`
      - `array` of `object` → repeatable field group with add/remove buttons
    - Pre-populate inputs with current values
  - Save button: `fetch('/settings', { method: 'POST', body: JSON.stringify(formData) })`
  - Success/error feedback: show a status message below the save button
  - Style using classes from `artimesone.css` (cards, form controls, buttons)
  - Reference: `Docs/artimesone-shared-platform.md` lines 224-252 for supported schema types
- **VALIDATE**:
  ```bash
  cd Agent-YouTube-Summary && uv run python -c "
  from fastapi.testclient import TestClient
  from agent_youtube_summary.app import app
  client = TestClient(app)
  resp = client.get('/settings')
  print('Settings page status:', resp.status_code)
  "
  ```

### Task 8: Implement rollup viewer routes

Build pages for browsing markdown rollup output files.

- **CREATE** `Agent-YouTube-Summary/src/agent_youtube_summary/routes/rollups.py`:
  - `router = APIRouter()`
  - `GET /` (home page) — Redirects to `/rollups` or renders a simple landing page. For MVP, redirect to rollups list is fine.
  - `GET /rollups` — List all rollup files:
    1. Scan `ROLLUP_OUTPUT_DIR` for `*.md` files
    2. Sort by filename descending (newest first — filenames are `YYYY-MM-DD.md`)
    3. Pass list to `rollups.html` template
  - `GET /rollups/{date}` — View a single rollup:
    1. Construct path: `ROLLUP_OUTPUT_DIR / {date}.md`
    2. Read the markdown file
    3. Convert markdown to HTML for display (use Python `markdown` library, or render raw markdown in a `<pre>` block, or simply pass to template and render with basic formatting)
    4. Pass content to `rollup_detail.html` template
    5. Return 404 if file doesn't exist
  - **PATTERN**: Follow existing file I/O pattern from `rollup.py:100-108` — use `Path` objects, `read_text(encoding="utf-8")`
  - **GOTCHA**: For MVP, rendering raw markdown as preformatted text or with basic line-by-line HTML conversion is acceptable. Adding a full markdown-to-HTML library (like `markdown` or `mistune`) is optional — it can be added later. A simple approach: split on `\n`, wrap headings in `<h1>`/`<h2>`/`<h3>`, wrap other lines in `<p>`. Or just use `<pre>` with white-space styling. The simplest viable approach: use the `markdown` package if you want nice rendering, or just serve the raw text in a styled container. Since the spec says "Vanilla JavaScript" for frontends, a lightweight client-side markdown renderer is also an option.
  - **DECISION**: Use a simple server-side approach. Don't add a new dependency just for markdown rendering. Render the raw markdown in a `<pre class="markdown-content">` block with CSS styling for readability. The rollup files are already well-structured with headings and lists that are readable as plain text.
- **CREATE** `Agent-YouTube-Summary/templates/rollups.html`:
  - Extends `base.html`
  - Title: "Rollups — YouTube Summary"
  - Content: list of rollup files as clickable links, grouped by date
  - Empty state: "No rollups yet. Run the pipeline to generate your first daily summary."
- **CREATE** `Agent-YouTube-Summary/templates/rollup_detail.html`:
  - Extends `base.html`
  - Title: "Rollup {date} — YouTube Summary"
  - Content: rendered markdown in a styled container
  - Back link to `/rollups`
- **VALIDATE**:
  ```bash
  cd Agent-YouTube-Summary && uv run python -c "
  from fastapi.testclient import TestClient
  from agent_youtube_summary.app import app
  client = TestClient(app)
  resp = client.get('/rollups')
  print('Rollups page status:', resp.status_code)
  "
  ```

### Task 9: Wire routes into the app and add server entry point

Connect the route modules to the FastAPI app. Add a way to start the server.

- **UPDATE** `Agent-YouTube-Summary/src/agent_youtube_summary/app.py`:
  - Import routers from routes package
  - Include routers: `app.include_router(settings_router)`, `app.include_router(rollups_router)`
- **VALIDATE**: Start the server and verify pages load:
  ```bash
  cd Agent-YouTube-Summary && timeout 5 uv run python -m agent_youtube_summary.app 2>&1 || true
  ```

### Task 10: Write tests for discovery module

- **CREATE** `Agent-YouTube-Summary/tests/test_discovery.py`:
  - Test `discover_agents()` function
  - Use `tmp_path` fixture to create mock workspace with `Agent-Foo/registry.json` and `Agent-Bar/registry.json`
  - **Test cases:**
    1. Happy path — discovers two agents from valid registry files, plus Dashboard entry
    2. Missing registry.json — directory is skipped
    3. Invalid JSON in registry.json — directory is skipped with warning
    4. Non-directory matching `Agent-*` pattern — skipped
    5. Empty workspace — returns only Dashboard entry
    6. Sort order — Platform category first, then Agents alphabetically
  - **PATTERN**: Follow existing test patterns from `conftest.py` — use `tmp_path`, direct assertions
  - **GOTCHA**: Create real directory structures in `tmp_path` with `mkdir()` and write JSON files for testing. Don't mock the filesystem — test real file scanning.
- **VALIDATE**:
  ```bash
  cd Agent-YouTube-Summary && uv run pytest tests/test_discovery.py -v
  ```

### Task 11: Write tests for web routes

- **CREATE** `Agent-YouTube-Summary/tests/test_app.py`:
  - Use `httpx.AsyncClient` with `ASGITransport` or `fastapi.testclient.TestClient` for testing
  - Mock `discover_agents` to return a fixed sidebar list (avoid depending on workspace layout)
  - Mock file system paths for settings and rollup files using `tmp_path` and `monkeypatch`
  - **Test cases:**
    - Settings page:
      1. `GET /settings` returns 200 with HTML containing form elements
      2. `POST /settings` with valid JSON saves to settings.json and returns `{"status": "ok"}`
      3. `POST /settings` with invalid/empty body returns error response
    - Rollups page:
      4. `GET /rollups` returns 200 with HTML
      5. `GET /rollups` with rollup files shows them listed
      6. `GET /rollups` with no files shows empty state message
      7. `GET /rollups/2026-04-05` with existing file returns 200 with content
      8. `GET /rollups/2026-04-05` with missing file returns 404
    - Home:
      9. `GET /` redirects to rollups (or returns 200 if it's a landing page)
  - **PATTERN**: Follow existing async test patterns. Use `monkeypatch` to override config values like `ROLLUP_OUTPUT_DIR`, `SETTINGS_PATH`, `WORKSPACE_DIR`, `SHARED_DIR`.
  - **GOTCHA**: The test client needs the shared templates and CSS to exist for the app to start. Either create minimal versions in `tmp_path` and monkeypatch `SHARED_DIR`, or mock the template rendering. Monkeypatching `SHARED_DIR` to point to a tmp directory with the required files is cleaner.
- **VALIDATE**:
  ```bash
  cd Agent-YouTube-Summary && uv run pytest tests/test_app.py -v
  ```

### Task 12: Run full validation suite

Ensure no regressions in existing tests and all new tests pass.

- **VALIDATE**: Run complete test suite:
  ```bash
  cd Agent-YouTube-Summary && uv run pytest -v
  ```
- **VALIDATE**: Lint and format:
  ```bash
  cd Agent-YouTube-Summary && uv run ruff check . && uv run ruff format --check .
  ```
- **VALIDATE**: Manual smoke test — start the server and verify in browser:
  ```bash
  cd Agent-YouTube-Summary && uv run python -m agent_youtube_summary.app
  # Open http://localhost:8001 — should see sidebar and home page
  # Open http://localhost:8001/settings — should see settings form
  # Open http://localhost:8001/rollups — should see rollup list (empty is OK)
  ```

---

## TESTING STRATEGY

### Unit Tests

- **test_discovery.py**: Test workspace scanning in isolation with `tmp_path` fixtures. No mocking of filesystem — create real directories and files. 6 test cases.
- **test_app.py**: Test HTTP routes using `TestClient` or `httpx.AsyncClient`. Mock `discover_agents` and filesystem paths. 9 test cases.

### Integration Tests

- The existing test suite (50 tests) covers the pipeline, database, settings, and rollup logic. These must continue to pass unchanged.
- Manual smoke test of the running web app against real shared assets.

### Edge Cases

- Workspace with no `Agent-*/` directories → sidebar shows only Dashboard
- `settings.json` missing on disk → settings page shows defaults
- `ROLLUP_OUTPUT_DIR` doesn't exist yet → rollups page shows empty state
- Malformed `registry.json` → agent skipped, others still load
- Concurrent settings save while pipeline is reading → last-write-wins (acceptable per spec)

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
cd Agent-YouTube-Summary && uv run ruff check .
cd Agent-YouTube-Summary && uv run ruff format --check .
```

**Expected**: All commands pass with exit code 0

### Level 2: Unit Tests

```bash
cd Agent-YouTube-Summary && uv run pytest tests/test_discovery.py tests/test_app.py -v
```

**Expected**: All new tests pass

### Level 3: Full Test Suite (regression)

```bash
cd Agent-YouTube-Summary && uv run pytest -v
```

**Expected**: All 50+ existing tests still pass, plus new tests

### Level 4: Manual Validation

1. Start the server: `cd Agent-YouTube-Summary && uv run python -m agent_youtube_summary.app`
2. Open `http://localhost:8001` — verify redirect or landing page
3. Open `http://localhost:8001/settings` — verify settings form renders with current values
4. Edit a setting, save — verify `settings.json` is updated
5. Open `http://localhost:8001/rollups` — verify rollup list (empty state if no rollups)
6. Verify sidebar appears on all pages with correct links and active highlighting
7. Click Dashboard link in sidebar — verify it points to `http://localhost:8000`

---

## ACCEPTANCE CRITERIA

- [ ] `shared/css/artimesone.css` exists with CSS custom properties, sidebar layout, and component styles
- [ ] `shared/templates/base.html` exists with sidebar, header, and content block
- [ ] `registry.json` uses `"url": "http://localhost:8001"` (not `route`)
- [ ] `widgets.schema.json` has no unresolvable bind parameters (`:last_visit` replaced)
- [ ] `.env.example` includes all shared platform variables (WORKSPACE_DIR, SHARED_DIR, DATA_DIR, HOST, PORT)
- [ ] `config.py` exports all shared platform variables; ROLLUP_OUTPUT_DIR derives from DATA_DIR
- [ ] `pyproject.toml` includes fastapi, uvicorn, jinja2 as dependencies
- [ ] FastAPI app starts on port 8001 and extends shared base template
- [ ] Sidebar renders correctly from scanned `Agent-*/registry.json` files
- [ ] Settings page loads schema, renders form, saves to `settings.json` on submit
- [ ] Rollup viewer lists markdown files and displays individual rollups
- [ ] All existing tests pass (zero regressions)
- [ ] All new tests pass (discovery + web routes)
- [ ] Ruff lint and format checks pass
- [ ] Code follows project conventions (async, type hints, logging, docstrings)

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully:
  - [ ] Level 1: ruff check, ruff format --check
  - [ ] Level 2: pytest (new tests)
  - [ ] Level 3: pytest (full suite, no regressions)
  - [ ] Level 4: Manual validation (server start, page load, settings save)
- [ ] Full test suite passes (unit + integration)
- [ ] No linting errors (uv run ruff check .)
- [ ] No formatting errors (uv run ruff format --check .)
- [ ] All acceptance criteria met
- [ ] Code reviewed for quality and maintainability

---

## EXECUTION STRATEGY

**Recommended approach**: Milestones

**Rationale**: 12 tasks with natural layering — shared infrastructure must exist before the web app can render, contract fixes are independent of web work, the web layer has internal dependencies (app factory before routes, routes before tests). Task-by-task would be unnecessarily granular for the simple early tasks. Whole-feature is too risky given the web layer complexity. Milestones group tightly-coupled work and provide validation checkpoints.

### Milestones

**Milestone 1: Foundation** (Tasks 1–4)
- Creates shared infrastructure, fixes contract files, updates config, adds web dependencies.
- **Validation checkpoint**: `shared/` directory exists with CSS and base template. Contract files are correct. `uv sync` succeeds with new dependencies. All existing tests still pass.

**Milestone 2: Web Application** (Tasks 5–9)
- Builds the discovery module, FastAPI app, settings page, rollup viewer, and wires them together.
- **Validation checkpoint**: Server starts on port 8001. Settings page renders and saves. Rollups page lists files. Sidebar shows discovered agents.

**Milestone 3: Tests & Validation** (Tasks 10–12)
- Writes new tests and runs the full validation suite.
- **Validation checkpoint**: All tests pass (existing + new). Ruff clean. Manual smoke test succeeds.

---

## NOTES

### LLM Model Decision (Not Addressed in This Plan)

The spec example shows `claude-haiku-4-5-20251001` as the default `summaryModel`, but the implementation uses `gpt-4o-mini` with the `openai` package. This plan does **not** change the LLM provider. It's a separate decision with its own implications (swapping the SDK, changing error handling, updating tests). If you decide to switch:
- Replace `openai` dependency with `anthropic` in `pyproject.toml`
- Rewrite `stage_summarize.py` to use `anthropic.AsyncAnthropic`
- Update the prompt format (Anthropic uses a different messages structure)
- Update all mocks in `test_stage_summarize.py`
- Update `settings.json` and `settings.schema.json` defaults

This should be a separate PR/task to keep this plan focused.

### Shared Utilities (Future)

The spec mentions shared Python utilities (`discover_agents()`, `connect_db()`, `read_settings()`, etc.) that could live in `shared/python/` or a `Utils-ArtimesOne` package. This plan implements `discover_agents()` inside the agent for now. When the Dashboard and other agents are built, this function should be extracted into a shared location to avoid duplication. For now, duplication across one agent is not duplication — it's the first implementation.

### CSS Scope

The `artimesone.css` created in Task 1 should be minimal but functional. It doesn't need to be polished — it needs to provide the sidebar layout, basic form styles, and card components so the agent's web UI is usable. Visual polish is a separate concern that can be iterated on once all agents have web UIs.
