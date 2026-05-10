# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **Angular 18 SPA** — replaced the Jinja2 / vanilla-JS frontend with a fully reactive single-page application (`frontend/`)
- **Microservices architecture** — split monolith into WebAPI (port 8001) + Worker Service (port 8002) + shared Database Service package
- **Group file explorer** — click any group tile to browse its full directory tree with collapsible folders; all folders start collapsed
- **Archive groups** — `POST /api/archive/{id}/archive` compresses a game group to a zip archive; live progress bar polls every 2 s
- **Unarchive / restore groups** — `POST /api/archive/{id}/restore` extracts the archive back to its original location with the same progress UI
- **Archived badge** — group tiles show a `✅ Archived` label once archived; explorer header button switches between Archive / Unarchive
- **Bulk icon refresh** — "Refresh All Icons" button in the Groups view with live `done / total` counter
- **Disk sidebar usage stats** — each disk entry now shows used / free / total space and a percentage bar (turns red above 85 %)
- **SVG favicon** — browser tab icon matches the monitor icon in the sidebar header
- GitHub Actions CI workflow (ruff + black + pytest)
- `SECURITY.md`, `CODE_OF_CONDUCT.md`, `ROADMAP.md`
- `pyproject.toml` for unified tooling configuration

### Fixed
- `GET /api/groups/` performance — was loading the cached `file_tree_json` column (several MB per group) for every row in the list query; now deferred. File counts switched from a correlated sub-query per group to a single `GROUP BY` aggregate query
- DLL deduplication scan O(n × m) bottleneck — `extract_dlls_inline` previously hashed every DLL in every other game group (800 + groups × thousands of files); replaced with an index-only lookup against `shared/index.json`
- `POST /api/groups/{id}/refresh-icon` returned HTTP 422 when a group had no `.exe`; now returns 200 with `{"skipped": true, "reason": "no_exe"}`
- Disk sidebar usage bar was reading `disk.percent` (undefined); corrected to `disk.pct_used` from the API response

---

## [1.0.0] - 2026-05-09

### Added
- Full-stack FastAPI + SQLite + Vanilla JS application
- Background disk scanning with live progress polling
- AI-powered file categorization (rule-based → scikit-learn → OpenAI fallback)
- File operations: move, rename, delete with safety checks
- Folder group detection and management
- Scan history (last 50 jobs)
- Cross-platform support: Windows and Linux
- Icon/thumbnail extraction via PowerShell (Windows) and file-icon (Linux)
- Interactive API docs at `/docs`
- Mermaid architecture diagram in README

[Unreleased]: https://github.com/Nori93/DiskAssistent/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Nori93/DiskAssistent/releases/tag/v1.0.0
