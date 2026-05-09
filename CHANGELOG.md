# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- GitHub Actions CI workflow (ruff + pytest)
- `SECURITY.md`, `CODE_OF_CONDUCT.md`, `ROADMAP.md`
- `pyproject.toml` for unified tooling configuration

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
