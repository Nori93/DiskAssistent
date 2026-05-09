# DiskAssistent

A full-stack file management web application built with **FastAPI**, **SQLite**, and **Vanilla JS**.
Supports Windows and Linux with AI-powered file categorization, background disk scanning, folder grouping, and drag-and-drop file operations.

---

## Features

- **Disk overview** — lists all available drives/mount points with free/used space
- **Background scanning** — recursive filesystem scan runs as a background job with live progress polling
- **AI categorization** — files are automatically categorized into Games, Movies, Documents, Music, Images, Software, or Other using a three-tier strategy:
  1. Rule-based heuristics (extension + path keywords)
  2. scikit-learn TF-IDF + Logistic Regression classifier (local, no API key required)
  3. OpenAI API fallback (optional, requires `OPENAI_API_KEY`)
- **File operations** — move, rename, and delete files with safety checks
- **Folder groups** — related folders are automatically detected and grouped
- **Scan history** — keeps a log of all past scan jobs
- **Cross-platform** — works on Windows and Linux

---

## Requirements

- Python 3.10+
- Dependencies listed in `requirements.txt`

---

## Installation

```bash
git clone https://github.com/your-username/DiskAssistent.git
cd DiskAssistent
pip install -r requirements.txt
```

---

## Running the App

```bash
python run.py
```

Then open your browser at [http://localhost:8000](http://localhost:8000).

Alternatively, run directly with uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The SQLite database (`database/diskassistent.db`) is created automatically on first run.

---

## Configuration

Environment variables (all optional):

| Variable | Default | Description |
|---|---|---|
| `APP_HOST` | `0.0.0.0` | Host address to bind |
| `APP_PORT` | `8000` | Port to listen on |
| `OPENAI_API_KEY` | _(unset)_ | Enables OpenAI-based categorization fallback |

---

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/disks/` | List available disks with usage info |
| `GET` | `/api/disks/tree` | Recursive directory tree for a given path |
| `POST` | `/api/scan/start` | Start a background scan job |
| `POST` | `/api/scan/rescan-all` | Wipe DB and rescan all disks |
| `GET` | `/api/scan/status/{job_id}` | Poll scan progress |
| `GET` | `/api/scan/active` | Get currently running scan job |
| `GET` | `/api/scan/history` | 50 most recent scan jobs |
| `GET` | `/api/files/` | Query/filter scanned files |
| `PATCH` | `/api/files/` | Update file metadata |
| `POST` | `/api/operations/move` | Move a file |
| `POST` | `/api/operations/rename` | Rename a file |
| `POST` | `/api/operations/delete` | Delete a file |
| `GET` | `/api/groups/` | List detected folder groups |
| `PATCH` | `/api/groups/` | Update group metadata |

Full interactive API docs available at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## Project Structure

```
DiskAssistent/
├── main.py                  ← FastAPI application entry point
├── run.py                   ← Convenience launcher
├── requirements.txt
│
├── backend/
│   ├── config.py            ← App settings, OS detection, logging
│   ├── routers/
│   │   ├── disks.py         ← GET /api/disks/
│   │   ├── scan.py          ← POST /api/scan/start, GET /api/scan/status/{id}
│   │   ├── files.py         ← GET/PATCH /api/files/
│   │   ├── operations.py    ← POST /api/operations/{move,rename,delete}
│   │   └── groups.py        ← GET/PATCH /api/groups/
│   └── services/
│       ├── scanner.py       ← Recursive filesystem scanning
│       ├── file_ops.py      ← Move / rename / delete with safety checks
│       ├── grouper.py       ← Folder group detection
│       └── scan_service.py  ← Background scan worker
│
├── database/
│   ├── models.py            ← SQLAlchemy models (FileRecord, FileGroup, ScanJob)
│   └── diskassistent.db     ← Auto-created on first run
│
├── ai/
│   └── categorizer.py       ← Rule-based + ML + optional OpenAI categorization
│
├── frontend/
│   ├── templates/
│   │   └── index.html       ← Jinja2 template served at /
│   └── static/
│       ├── css/style.css
│       └── js/
│           ├── api.js       ← REST API wrapper
│           ├── ui.js        ← UI helpers (toast, modals, charts)
│           └── app.js       ← Main application logic
│
└── logs/
    └── app.log
```

---

## License

MIT

---

## ⚡ Quick Start

### 1. Prerequisites

- Python 3.10 or newer
- pip

### 2. Install dependencies

```bash
cd DiskAssistent
pip install -r requirements.txt
```

### 3. Run

```bash
python run.py
```

Or directly with uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Open in browser

```
http://localhost:8000
```

---

## 🔧 Environment Variables

| Variable         | Default     | Description                           |
|------------------|-------------|---------------------------------------|
| `APP_HOST`       | `0.0.0.0`   | Bind host                             |
| `APP_PORT`       | `8000`      | Bind port                             |
| `OPENAI_API_KEY` | _(empty)_   | Optional — enables OpenAI fallback    |

---

## 🖥️ Cross-Platform Notes

- On **Windows**: disk list is built from Windows drive letters (A–Z).
- On **Linux/macOS**: disk list uses `psutil.disk_partitions()` (requires `psutil`).
- File paths use `pathlib.Path` throughout, so separators are handled automatically.

---

## 🤖 AI Categorization

Files are categorized using a 3-tier system:

1. **Rule-based heuristics** — extension + keyword matching (always runs, no deps).
2. **scikit-learn classifier** — TF-IDF + Logistic Regression trained on synthetic data (runs locally).
3. **OpenAI fallback** — only when `OPENAI_API_KEY` is set.

Users can manually override any category from the file detail modal.

---

## 📡 API Reference

| Method   | Endpoint                         | Description                  |
|----------|----------------------------------|------------------------------|
| GET      | `/api/disks/`                    | List disks with usage info   |
| GET      | `/api/disks/tree?path=…`         | Folder tree                  |
| POST     | `/api/scan/start`                | Start background scan job    |
| GET      | `/api/scan/status/{id}`          | Poll scan progress           |
| GET      | `/api/files/`                    | List/search/filter files     |
| GET      | `/api/files/stats`               | Aggregate statistics         |
| GET      | `/api/files/{id}`                | Single file detail           |
| PATCH    | `/api/files/{id}`                | Update category/tags/desc    |
| POST     | `/api/operations/move`           | Move a file                  |
| POST     | `/api/operations/rename`         | Rename a file                |
| DELETE   | `/api/operations/delete`         | Delete a file (confirm=true) |
| GET      | `/api/groups/`                   | List detected groups         |
| GET      | `/api/groups/{id}`               | Group detail with files      |
| PATCH    | `/api/groups/{id}`               | Update group metadata        |

Interactive API docs available at: `http://localhost:8000/docs`

---

## 🔒 Security Notes

- File operations require explicit confirmation from the client.
- Delete endpoint requires `confirm: true` in the request body.
- File names are sanitised before rename operations.
- System directories (Windows, System32, /proc, /sys, etc.) are skipped during scanning.

---

## 📦 Optional Enhancements

To enable duplicate file detection, image thumbnails, or user authentication, see the issues/roadmap in the repository.
