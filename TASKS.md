# Project Task List

## 🔧 Core Functionality

* [ ] Replace the per-file ORM loop in `_run_scan` (`scan_service.py`) with the same bulk-upsert strategy (`_upsert_file_batch`) already used by `_run_rescan_all` — the current single-scan path issues one `SELECT` + one `INSERT/UPDATE` per file, making large scans orders of magnitude slower than rescan-all.
* [ ] Directory is walked twice in `_run_scan` (once to count, once to index) — combine into a single pass using an estimated count or stream-count approach to halve I/O time.
* [ ] Combine `_count_files_recursive` and `_sum_size_recursive` in `grouper.py` into a single `os.walk` call to avoid double filesystem traversal when building group descriptors.
* [ ] Replace all `datetime.datetime.utcnow()` calls across `database/models.py`, `scan_service.py`, and `recategorize_service.py` with `datetime.datetime.now(datetime.timezone.utc)` — `utcnow()` is deprecated in Python 3.12 and returns a naïve datetime that can cause timezone bugs.
* [ ] The `cleanup` endpoint in `backend/routers/files.py` runs synchronously on the request thread, making one `os.path.exists` call per indexed file — move it to a background worker to avoid blocking the API under large databases.
* [ ] Add a `PATCH /api/files/` (bulk update) endpoint or correct the README which incorrectly lists it; the actual route is `PATCH /api/files/{id}` (single file).
* [ ] Add `GET /api/scan/rescan-all` status polling route or document that the same `GET /api/scan/status/{job_id}` is used — the frontend uses it correctly but the API table in the README is missing this detail.
* [ ] The `DiskAssistent.session.sql` file is an empty DB IDE artifact and should be excluded via `.gitignore`, not committed to the repository.
* [ ] Implement image thumbnail generation for image files (`.jpg`, `.png`, `.webp`, etc.) stored in `THUMBNAILS_DIR` — the infrastructure and URL prefix already exist in `icon_service.py` and `config.py` but the actual thumbnail generation is not implemented.
* [ ] Add duplicate file detection based on file size + name (or hash) — noted as a future enhancement in README.

## 🐛 Bug Fixes

* [ ] In `app.js`, the cleanup button's success handler calls `loadCategoryGroups()` without a `category` argument — the function signature requires a category string and will throw a JS error; it should be `loadCategoryGroups(STATE.currentCategory)` or branch to `loadFiles()`.
* [ ] The `bindEvents()` function in `app.js` is defined as an empty stub and then called on `DOMContentLoaded`, but all event listeners are attached at module level — either populate `bindEvents()` or remove the dead call to avoid confusion.
* [ ] The `GET /api/scan/active` endpoint returns `{"job_id": None}` (null) when no scan is running, but `ScanJob.to_dict()` returns `{"id": ...}` when one is found — the frontend JS checks `active.id` which works by coincidence; standardise the response shape to always use `job_id`.
* [ ] Icon extraction in `icon_service.py` writes the temporary `.ps1` script into `THUMBNAILS_DIR` — use `tempfile.NamedTemporaryFile` or the system temp directory instead to prevent the script file appearing in the static web-accessible path.
* [ ] The drag-and-drop handler in `app.js` attaches `dragover`/`drop` to `#file-tbody` but there is no visible drop-target UI for folder destinations — the drop currently has no functional destination and likely fails silently; implement a proper drag-to-folder-tile move flow or remove the incomplete feature flag.
* [ ] `FileRecord.scanned_at` uses a mutable default `datetime.datetime.utcnow` (without calling it) as the SQLAlchemy `default` — this is correct for SQLAlchemy but should be `datetime.datetime.now` with `timezone.utc` for consistency with the deprecation fix above.
* [ ] `_migrate_add_columns` in `database/models.py` has no migration entries for the `RecategorizeJob` table columns added after initial release — if users upgrade from an older schema, the table won't have the correct columns and queries will fail.

## 🚀 Improvements

* [ ] Replace `prompt()` and `confirm()` native browser dialogs in `app.js` (used for rename destination, move destination, and rescan-all confirmation) with proper in-page modal dialogs — native dialogs can be blocked by browsers and provide a poor UX.
* [ ] Add sorting controls to the file list view (`app.js` / `backend/routers/files.py`) — currently files are always sorted by name; users should be able to sort by size, date, or category.
* [ ] Add filtering by `missing=true` to the UI sidebar or file list header — the API supports the `missing` query parameter but there is no frontend control to surface it.
* [ ] Make `CORS allow_origins=["*"]` in `main.py` configurable via an environment variable so it can be locked down when the app is exposed beyond localhost.
* [ ] Add rate limiting to the scan/rescan endpoints (`backend/routers/scan.py`) to prevent accidental simultaneous submission of multiple full-disk scans.
* [ ] Replace the Google Fonts CDN `<link>` in `index.html` with a locally-bundled font or make it opt-in — the CDN call breaks the app in offline/air-gapped environments and leaks the user's IP to Google.
* [ ] Add a configurable `MAX_SCAN_SIZE` filter in `scan_service.py` — the config value exists in `config.py` but is hardcoded to `0` (disabled) and never applied during scanning.
* [ ] Add sorting and filtering to the Groups view — currently all groups are listed without any ordering or category filter in the all-groups view.
* [ ] Persist view mode (`list` / `grid`) and last selected category in `localStorage` so the UI state survives page refreshes.
* [ ] Expose `AI_BASE_URL` and `AI_MODEL` configuration in the README environment variables table — they are implemented in `config.py` and `categorizer.py` but undocumented for users.
* [ ] Add a configurable poll interval for scan/recategorize status polling (currently hardcoded to 1200–1500 ms in `app.js`) to reduce API load on slow machines.

## 🧪 Testing

* [ ] Add unit tests for `ai/categorizer.py` — specifically `_rule_based()`, `_ml_categorize()`, and the full `categorize()` pipeline with mocked OpenAI calls.
* [ ] Add unit tests for `backend/services/file_ops.py` — cover move, rename, and delete success and failure paths using `tmp_path` fixtures.
* [ ] Add unit tests for `backend/services/grouper.py` — cover `_find_group_root`, `_game_root_from_anchor`, and `detect_groups` with synthetic directory trees.
* [ ] Add integration tests for all API routers using FastAPI `TestClient` and an in-memory SQLite database.
* [ ] Add tests for `database/models.py` — verify `to_dict` output shape, `_human_size` edge cases, and `_migrate_add_columns` idempotency.
* [ ] Add a CI workflow (GitHub Actions) that runs the test suite on push and pull requests for Python 3.10, 3.11, and 3.12.

## 📚 Documentation

* [ ] Document the `AI_BASE_URL` and `AI_MODEL` environment variables in the README (Ollama and LM Studio integration is implemented but not mentioned in docs).
* [ ] Add a `CONTRIBUTING.md` file describing how to set up a dev environment, run tests, and submit PRs.
* [ ] Add an `CHANGELOG.md` to track releases and breaking changes.
* [ ] Document the `RecategorizeJob` model and `/api/files/recategorize` endpoints in the README API table — they are fully implemented but missing from the docs.
* [ ] Document the `POST /api/operations/open-folder` endpoint and `POST /api/files/regroup` endpoint — both implemented but absent from the README API reference.
* [ ] Clarify in the README that icon extraction (`refresh-icon` endpoint) is Windows-only and requires PowerShell.

## ⚙️ DevOps / Setup

* [ ] Add `DiskAssistent.session.sql` and `*.session.sql` to `.gitignore` — the file is currently committed but is an IDE artifact with no content.
* [ ] Add a `pyproject.toml` or `setup.cfg` with project metadata, Python version constraint (`>=3.10`), and tool configuration (linting, formatting) to replace the ad-hoc `requirements.txt`-only setup.
* [ ] Add a `Dockerfile` and `docker-compose.yml` for containerised deployment so the app can run without a local Python installation.
* [ ] Add a pre-commit hook configuration (`.pre-commit-config.yaml`) with `ruff` or `flake8` and `black` to enforce code style on commit.
* [ ] Pin all dependencies in `requirements.txt` to exact versions (they are already pinned — ensure a `requirements-dev.txt` is added for test/lint dependencies such as `pytest`, `httpx`, `ruff`).
* [ ] Add a `logs/.gitkeep` file and include `logs/*.log` in `.gitignore` so the `logs/` directory is tracked but log files are not.
