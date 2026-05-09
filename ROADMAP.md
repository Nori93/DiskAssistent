# Roadmap

This document outlines planned features and improvements for DiskAssistent.
Items are grouped by theme and roughly ordered by priority. Community feedback
and PRs are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## UI / UX

- [ ] **Dark / light theme** with preference saved in `localStorage`
- [ ] **Live stats panel** — pie charts for category usage, file-size histograms, scan timeline
- [ ] **Treemap view** — visualise disk usage as proportionally sized squares per group/folder
- [ ] **File quick-preview** — in-browser viewer for images, plain text, and PDF
- [ ] **Global search shortcut** (Ctrl+K / Cmd+K) with full-text search by name, tags, and description

---

## AI Categorization

- [ ] **User-trained ML model** — classifier improves over time based on manual overrides
- [ ] **Auto-tags from metadata** — EXIF (images), ID3 (audio), document headings
- [ ] **Duplicate detection** — SHA-256 hash comparison with one-click removal
- [ ] **Custom categorization rules** — user-defined rules (e.g. "everything in `Faktury/` → Documents")

---

## File Operations

- [ ] **Bulk move / rename** — select multiple files and operate on the whole selection
- [ ] **Operation history & undo** — every move/rename/delete is logged and reversible
- [ ] **Scheduled auto-scan** — periodic background scans without user interaction

---

## Backup

- [ ] **Backup target configuration** — UNC shares, local folders, future: WebDAV / SFTP
- [ ] **Scope selection** — back up a single file, group, category, or all present files
- [ ] **Operation modes** — copy, move, or mirror (delta sync by date + size)
- [ ] **Progress tracking** — same polling mechanism as scan jobs
- [ ] **Integrity verification** — optional SHA-256 comparison after transfer

Planned API:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/backup/targets` | List configured backup targets |
| `POST` | `/api/backup/targets` | Add a new target |
| `POST` | `/api/backup/start`   | Start a backup job |
| `GET`  | `/api/backup/status/{job_id}` | Poll job progress |
| `GET`  | `/api/backup/history` | History of completed backups |

---

## Security & Multi-user

- [ ] **User authentication** — roles (Admin, Read-only) with JWT sessions
- [ ] **Activity log** — who did what to which file, and when
- [ ] **HTTPS out-of-the-box** — built-in Let's Encrypt or custom certificate support

---

## Developer Experience

- [ ] **Pre-commit hooks** — `ruff` + `black` enforced before every commit
- [ ] **Integration test suite** — coverage for all API endpoints
- [ ] **Docker image** — single-container deployment with volume mounts for data and thumbnails
