# DiskAssistent

A full-stack file management web application built with **Angular 18**, **FastAPI**, and **SQLite**.
Supports Windows and Linux with AI-powered file categorization, background disk scanning, folder grouping, and file operations.

> **Current branch:** `develop` — the application runs as a hybrid: the Worker Service runs natively on Windows for full filesystem access, while the WebAPI and Frontend can optionally run in Podman containers.

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
- **Archiving & deduplication** — archive groups and find duplicate files
- **Scan history** — keeps a log of all past scan jobs
- **Cross-platform** — works on Windows and Linux

---

## Architecture

```mermaid
flowchart TB
    subgraph Browser["🌐 Browser"]
        SPA["Angular 18 SPA\napp.component.ts"]
        API_SVC["api.service.ts\nHTTP client"]
        SPA --> API_SVC
    end

    subgraph WebAPI["⚡ WebAPI — FastAPI webapi/ :8001"]
        W_DISKS["routers/disks.py\n/api/disks/"]
        W_FILES["routers/files.py\n/api/files/"]
        W_GROUPS["routers/groups.py\n/api/groups/"]
        W_OPS["routers/operations.py\n/api/operations/"]
        W_PROXY["Reverse Proxy\n/api/scan /api/archive /api/dedup"]
    end

    subgraph Worker["⚙️ Worker Service — FastAPI worker-service/ :8002"]
        WK_SCAN["routers/scan.py\n/api/scan/"]
        WK_ARCHIVE["routers/archive.py\n/api/archive/"]
        WK_DEDUP["routers/dedup.py\n/api/dedup/"]
        WK_RECAT["routers/recategorize.py\n/api/files/recategorize"]
    end

    subgraph WorkerSvc["🔧 Worker Services"]
        SVC_SCAN["scan_service.py\nBackground scan worker"]
        SVC_SCANNER["scanner.py\nFilesystem walker"]
        SVC_GROUPER["grouper.py\nGroup detection"]
        SVC_ARCHIVE["archive_service.py\nzip + restore"]
        SVC_DEDUP["dedup_service.py\nShared DLL index"]
        SVC_RECAT["recategorize_service.py\nAI re-label worker"]
        SVC_ICON["icon_service.py\nIcon extraction"]
        SVC_FILE_OPS["file_ops.py\nMove / rename / delete"]
        EXECUTOR["ThreadPoolExecutor\nmax_workers=1"]
    end

    subgraph AI["🤖 AI Categorization ai/"]
        AI_RULES["Rule-based heuristics\nextension + path keywords"]
        AI_ML["TF-IDF + LogisticRegression\nscikit-learn"]
        AI_LLM["OpenAI API fallback\noptional OPENAI_API_KEY"]
        AI_RULES --> AI_ML --> AI_LLM
    end

    subgraph DbPkg["📦 Database Service database-service/"]
        MODELS["diskassistent_db/models.py\nFileRecord · FileGroup · ScanJob\nArchiveJob · RecategorizeJob"]
    end

    subgraph Data["🗄️ Storage"]
        DB[("SQLite\ndatabase/diskassistent.db")]
        FS["Local filesystem\ndisk drives"]
        THUMBS["frontend/static/img/thumbnails/\nPNG icons"]
        ZIPSTORE["Archive directory\nconfigurable"]
        SHARED["Shared DLL directory\nconfigurable"]
    end

    API_SVC -->|"HTTP REST /api/*"| WebAPI
    W_PROXY -->|"HTTP :8002"| Worker

    W_DISKS --> SVC_SCANNER
    W_FILES --> DbPkg
    W_GROUPS --> DbPkg
    W_OPS --> SVC_FILE_OPS

    WK_SCAN --> SVC_SCAN
    WK_ARCHIVE --> SVC_ARCHIVE
    WK_DEDUP --> SVC_DEDUP
    WK_RECAT --> SVC_RECAT

    SVC_SCAN --> EXECUTOR
    SVC_ARCHIVE --> EXECUTOR
    SVC_RECAT --> EXECUTOR

    SVC_SCAN --> SVC_SCANNER
    SVC_SCAN --> SVC_GROUPER
    SVC_SCAN --> SVC_ICON
    SVC_RECAT --> SVC_GROUPER

    SVC_SCANNER --> AI
    SVC_RECAT --> AI

    SVC_SCAN --> DbPkg
    SVC_ARCHIVE --> DbPkg
    SVC_DEDUP --> DbPkg
    SVC_RECAT --> DbPkg
    SVC_FILE_OPS --> DbPkg

    DbPkg --> DB
    SVC_SCANNER --> FS
    SVC_FILE_OPS --> FS
    SVC_ICON -->|"PowerShell .exe to PNG"| THUMBS
    SVC_ARCHIVE --> ZIPSTORE
    SVC_DEDUP --> SHARED
```

### Service Summary

| Service | Folder | Port | Run mode | Role |
|---|---|---|---|---|
| **Frontend** | `frontend/` | 4200 | Native (ng serve) or Podman container | Angular 18 SPA |
| **WebAPI** | `webapi/` | 8001 | Native or Podman container | REST API for UI — fast read/write |
| **Worker Service** | `worker-service/` | 8002 | **Always native** (Windows) | Heavy background tasks (scan, archive, dedup, AI) |
| **Database Service** | `database-service/` | — | Shared package | All SQLAlchemy models |

> The Worker Service runs natively because it needs direct access to Windows disk drives and the filesystem. In container mode the WebAPI reaches it via `http://host.containers.internal:8002`.

---

## Requirements

### Python services (WebAPI + Worker)
- Python 3.10+
- A virtual environment at `.venv/` is recommended

### Frontend
- Node.js 18+ and npm

### Containers (optional)
- [Podman Desktop](https://podman.io/) with WSL2 backend

---

## Installation

```bash
git clone https://github.com/Nori93/DiskAssistent.git
cd DiskAssistent
```

**Create a virtual environment and install all Python dependencies:**

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r webapi/requirements.txt
pip install -r worker-service/requirements.txt
pip install -e database-service/
```

**Install frontend dependencies:**

```bash
cd frontend
npm install
cd ..
```

---

## Running All Services

### Option A: VS Code — one-click launch (recommended)

Open the **Run & Debug** panel (`Ctrl+Shift+D`) and select **"All Services (native dev)"** from the dropdown, then press **F5**.

This runs the VS Code task **"All Services: Start (native)"** which starts all three services in dedicated terminal panels:
- Worker Service on `:8002` (with `--reload`)
- WebAPI on `:8001` (with `--reload`)
- Angular dev server on `:4200`

Then opens Chrome at [http://localhost:4200](http://localhost:4200).

> **Why tasks and not debugpy launch configs?** On Windows, `debugpy` attaches to the Python process via a shared console group. Any console signal (including those from VS Code's task runner) gets broadcast to all processes in that group, causing uvicorn to shut down immediately. Running as plain shell tasks avoids this entirely. To debug with breakpoints, use the individual **"WebAPI"** or **"Worker Service"** launch configs.

### Option B: Manual terminals

Open three separate terminals with the venv activated (`.venv\Scripts\activate`):

**Terminal 1 — Worker Service**
```powershell
cd worker-service
$env:PYTHONPATH = "$PWD;$PWD\..\database-service"
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

**Terminal 2 — WebAPI**
```powershell
cd webapi
$env:PYTHONPATH = "$PWD;$PWD\..\database-service"
$env:WORKER_URL = "http://localhost:8002"
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 3 — Frontend**
```powershell
cd frontend
node ./node_modules/@angular/cli/bin/ng serve --proxy-config proxy.conf.json
```

Then open your browser at [http://localhost:4200](http://localhost:4200).

The SQLite database (`database/diskassistent.db`) is created automatically on first run.

### Option C: Podman containers (WebAPI + Frontend) + native Worker

Run the VS Code task **"Podman: Build & Start"** (builds and starts the `webapi` and `frontend` containers), then start the Worker Service natively as in Option B Terminal 1.

Or use the **"Podman + Worker (native)"** compound in the Run & Debug panel.

```powershell
# Manually:
.\podman-up.ps1 -Build          # build + start webapi + frontend containers
# Worker must run natively (see Terminal 1 above)
```

Container management:
```powershell
.\podman-up.ps1                  # start containers (no rebuild)
.\podman-up.ps1 -Build           # rebuild + start
.\podman-up.ps1 -Build -NoStart  # build images only
.\podman-up.ps1 -Down            # stop and remove containers
```

---

## Legacy Monolith

The original single-process version is still available on the `main` branch:

```bash
git checkout main
python run.py            # http://localhost:8000
```

---

## Configuration

### Environment variables

| Variable | Service | Default | Description |
|---|---|---|---|
| `WEBAPI_PORT` | WebAPI | `8001` | Port for WebAPI |
| `WORKER_URL` | WebAPI | `http://localhost:8002` | Worker Service base URL (set to `http://host.containers.internal:8002` in container mode) |
| `WORKER_PORT` | Worker | `8002` | Port for Worker Service |
| `DISKASSISTENT_DB_PATH` | Both | `<repo>/database/diskassistent.db` | SQLite database path |
| `OPENAI_API_KEY` | Worker | _(unset)_ | Enables OpenAI categorization fallback |
| `AI_BASE_URL` | Worker | _(unset)_ | Custom OpenAI-compatible API base URL |
| `AI_MODEL` | Worker | `gpt-3.5-turbo` | Model name for AI categorization |

---

## Project Structure

```
DiskAssistent/
│
├── database-service/           ← Shared Python package (diskassistent-db)
│   └── diskassistent_db/
│       ├── config.py           ← DB path + logger
│       └── models.py           ← All SQLAlchemy models & init_db()
│
├── webapi/                     ← FastAPI — port 8001
│   ├── main.py                 ← App entry point + proxy to Worker
│   ├── config.py               ← Port, WORKER_URL, logging
│   ├── requirements.txt
│   ├── routers/
│   │   ├── disks.py            ← GET /api/disks/
│   │   ├── files.py            ← GET/PATCH /api/files/
│   │   ├── groups.py           ← GET/PATCH /api/groups/
│   │   └── operations.py       ← POST /api/operations/{move,rename,delete}
│   └── services/
│       ├── scanner.py          ← Disk listing + directory tree
│       ├── file_ops.py         ← Move / rename / delete
│       └── settings_service.py ← Load / save settings.json
│
├── worker-service/             ← FastAPI — port 8002
│   ├── main.py                 ← App entry point + resume interrupted scans
│   ├── config.py               ← Port, logging
│   ├── requirements.txt
│   ├── routers/
│   │   ├── scan.py             ← POST /api/scan/start, GET /api/scan/status/{id}
│   │   ├── archive.py          ← POST /api/archive/{id}/archive, /restore
│   │   ├── dedup.py            ← POST /api/dedup/analyze, /apply
│   │   └── recategorize.py     ← POST /api/files/recategorize
│   ├── services/               ← Heavy processing workers
│   │   ├── scan_service.py
│   │   ├── archive_service.py
│   │   ├── dedup_service.py
│   │   ├── recategorize_service.py
│   │   ├── grouper.py
│   │   ├── scanner.py
│   │   └── settings_service.py
│   └── ai/
│       └── categorizer.py      ← Rule-based + ML + optional OpenAI
│
├── frontend/                   ← Angular 18 SPA — port 4200
│   ├── proxy.conf.json         ← /api → http://localhost:8001
│   ├── src/app/
│   │   ├── app.routes.ts
│   │   ├── app.config.ts
│   │   ├── services/
│   │   │   └── api.service.ts  ← Typed HTTP client for all endpoints
│   │   └── components/
│   │       ├── dashboard/
│   │       ├── disk-list/
│   │       ├── file-browser/
│   │       ├── groups/
│   │       ├── settings/
│   │       └── sidebar/
│   └── angular.json
│
├── database/
│   └── diskassistent.db        ← Auto-created SQLite database
│
├── logs/
│   ├── webapi.log
│   └── worker.log
│
├── settings.json               ← Archive/dedup directory settings
│
│   ── Legacy monolith (main branch) ──
├── main.py
├── run.py
├── requirements.txt
├── backend/
├── ai/
└── frontend/ (old Jinja2/vanilla JS)
```

---

## API Reference

All endpoints are served by the WebAPI on port 8001. Heavy operations are transparently proxied to the Worker Service on port 8002.

### Disks
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/disks/` | List disks with usage info |
| GET | `/api/disks/tree?path=…` | Folder tree |

### Scan (proxied to Worker)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/scan/start` | Start background scan job |
| GET | `/api/scan/status/{id}` | Poll scan progress |
| GET | `/api/scan/active` | Currently running scan |
| GET | `/api/scan/history` | 50 most recent scan jobs |
| POST | `/api/scan/rescan-all` | Wipe DB and rescan all disks |

### Files
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/files/` | List/search/filter files |
| GET | `/api/files/stats` | Aggregate statistics |
| GET | `/api/files/{id}` | Single file detail |
| PATCH | `/api/files/{id}` | Update category/tags/desc |
| POST | `/api/files/recategorize` | Re-run AI categorization |
| POST | `/api/files/cleanup` | Remove missing file records |

### Groups
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/groups/` | List detected folder groups |
| GET | `/api/groups/{id}` | Group detail with files |
| PATCH | `/api/groups/{id}` | Update group metadata |
| DELETE | `/api/groups/{id}` | Delete a group |
| POST | `/api/groups/{id}/refresh-icon` | Re-extract group icon from an executable (Windows only; requires PowerShell) |

### Operations
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/operations/move` | Move a file |
| POST | `/api/operations/rename` | Rename a file |
| DELETE | `/api/operations/delete` | Delete a file (confirm=true) |
| POST | `/api/operations/open-folder` | Open folder in OS explorer |

### Archive (proxied to Worker)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/archive/settings` | Get archive/dedup settings |
| PUT | `/api/archive/settings` | Update settings |
| POST | `/api/archive/{id}/archive` | Archive a group |
| POST | `/api/archive/{id}/restore` | Restore an archived group |
| GET | `/api/archive/{id}/status` | Archive job status |

### Dedup (proxied to Worker)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/dedup/analyze` | Find duplicate files |
| POST | `/api/dedup/apply` | Apply deduplication (hardlinks) |
| POST | `/api/dedup/restore` | Restore originals |
| GET | `/api/dedup/stats` | Dedup space savings |

Interactive API docs: `http://localhost:8001/docs` (WebAPI) · `http://localhost:8002/docs` (Worker)

---

## 🤖 AI Categorization

Files are categorized using a 3-tier system:

1. **Rule-based heuristics** — extension + keyword matching (always runs, no deps)
2. **scikit-learn classifier** — TF-IDF + Logistic Regression trained on synthetic data (runs locally)
3. **OpenAI fallback** — only when `OPENAI_API_KEY` is set

Users can manually override any category from the file detail view.

---

## 🖥️ Cross-Platform Notes

- On **Windows**: disk list is built from Windows drive letters (A–Z).
- On **Linux/macOS**: disk list uses `psutil.disk_partitions()`.
- File paths use `pathlib.Path` throughout, so separators are handled automatically.
- Icon extraction, including `POST /api/groups/{id}/refresh-icon`, is
  Windows-only and requires `powershell.exe`.

---

## 🔒 Security Notes

- File operations require explicit confirmation from the client.
- Delete endpoint requires `confirm: true` in the request body.
- File names are sanitised before rename operations.
- System directories (Windows, System32, /proc, /sys, etc.) are skipped during scanning.

---

## License

MIT — see [LICENSE](LICENSE) for full text.

If you use DiskAssistent in a commercial product or organisation, we'd love to hear about it — drop us a message at **[norbert.wieczorek.93@gmail.com](mailto:norbert.wieczorek.93@gmail.com)**. It's not required, just appreciated.


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

## 🏗️ Architektura aplikacji

```mermaid
graph TB
    subgraph Browser["🌐 Przeglądarka"]
        direction TB
        UI["index.html\nJinja2 Template"]
        JS_APP["app.js\nGłówna logika"]
        JS_API["api.js\nREST wrapper"]
        JS_UI["ui.js\nKomponenty UI"]
        UI --> JS_APP
        JS_APP --> JS_API
        JS_APP --> JS_UI
    end

    subgraph FastAPI["⚡ FastAPI (main.py)"]
        direction TB
        R_DISKS["routers/disks.py\n/api/disks/"]
        R_SCAN["routers/scan.py\n/api/scan/"]
        R_FILES["routers/files.py\n/api/files/"]
        R_OPS["routers/operations.py\n/api/operations/"]
        R_GROUPS["routers/groups.py\n/api/groups/"]
    end

    subgraph Services["🔧 Serwisy"]
        direction TB
        SVC_SCANNER["scanner.py\nSkanowanie FS"]
        SVC_SCAN_SVC["scan_service.py\nWorker skanowania"]
        SVC_GROUPER["grouper.py\nWykrywanie grup"]
        SVC_RECATEGORIZE["recategorize_service.py\nWorker rekategoryzacji"]
        SVC_FILE_OPS["file_ops.py\nOperacje na plikach"]
        SVC_ICON["icon_service.py\nEkstrakcja ikon"]
    end

    subgraph AI["🤖 AI / Kategoryzacja"]
        AI_RULES["Reguły + rozszerzenia"]
        AI_ML["TF-IDF + LogisticRegression\n(scikit-learn)"]
        AI_LLM["OpenAI / Ollama / LM Studio\n(opcjonalnie)"]
        AI_RULES --> AI_ML --> AI_LLM
    end

    subgraph Data["🗄️ Dane"]
        DB[("SQLite\ndiskassistent.db")]
        FS["System plików\n(dyski lokalne)"]
        THUMBS["static/img/thumbnails/\n(ikony PNG)"]
    end

    subgraph Background["⚙️ Wątki w tle"]
        EXECUTOR["ThreadPoolExecutor\nmax_workers=1"]
    end

    JS_API -->|"HTTP REST"| FastAPI
    R_SCAN --> SVC_SCAN_SVC
    R_FILES --> SVC_RECATEGORIZE
    R_FILES --> SVC_FILE_OPS
    R_GROUPS --> SVC_GROUPER
    R_DISKS --> SVC_SCANNER
    R_OPS --> SVC_FILE_OPS

    SVC_SCAN_SVC --> EXECUTOR
    SVC_RECATEGORIZE --> EXECUTOR
    SVC_SCAN_SVC --> SVC_SCANNER
    SVC_SCAN_SVC --> SVC_GROUPER
    SVC_SCAN_SVC --> SVC_ICON
    SVC_RECATEGORIZE --> SVC_GROUPER

    SVC_SCANNER --> AI
    SVC_GROUPER --> AI

    SVC_SCAN_SVC --> DB
    SVC_RECATEGORIZE --> DB
    SVC_FILE_OPS --> DB
    R_FILES --> DB
    R_GROUPS --> DB

    SVC_SCANNER --> FS
    SVC_FILE_OPS --> FS
    SVC_ICON -->|"PowerShell .exe → PNG"| THUMBS
```

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

MIT — see [LICENSE](LICENSE) for full text.

If you use DiskAssistent in a commercial product or organisation, we'd love to hear about it — drop us a message at **[norbert.wieczorek.93@gmail.com](mailto:norbert.wieczorek.93@gmail.com)**. It's not required, just appreciated.

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
- Icon extraction, including `POST /api/groups/{id}/refresh-icon`, is
  Windows-only and requires `powershell.exe`.

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
| POST     | `/api/groups/{id}/refresh-icon`  | Re-extract group icon (Windows only; requires PowerShell) |

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

---

## 🔮 Przyszłościowy wygląd aplikacji

DiskAssistent jest rozwijany jako pełnoprawne centrum zarządzania plikami w sieci domowej i małym biurze. Poniżej plan dalszego rozwoju:

### Interfejs użytkownika
- **Ciemny / jasny motyw** z zapisem preferencji w przeglądarce
- **Panel statystyk na żywo** — wykresy kołowe zajętości kategorii, histogramy rozmiarów plików i oś czasu skanowań
- **Widok mapy drzewa (Treemap)** — wizualizacja dysku jako kwadratów proporcjonalnych do rozmiaru grup i folderów
- **Szybki podgląd plików** — wbudowany viewer dla obrazów, tekstów i PDF bezpośrednio w oknie przeglądarki
- **Globalny skrót wyszukiwania** (Ctrl+K / Cmd+K) z wyszukiwaniem pełnotekstowym po nazwie, tagach i opisie

### Inteligentna kategoryzacja
- **Model ML trenowany na własnych danych** użytkownika — im dłużej aplikacja działa, tym lepiej rozumie kolekcję
- **Tagi automatyczne** generowane na podstawie metadanych EXIF (zdjęcia), ID3 (muzyka) i nagłówków dokumentów
- **Wykrywanie duplikatów** — porównanie po rozmiarze i haszowaniu SHA-256 z możliwością usunięcia w jednym kliknięciu
- **Reguły niestandardowe** — użytkownik definiuje własne reguły kategoryzacji (np. „wszystko z folderu `Faktury/` → Documents")

### Operacje na plikach
- **Masowe przenoszenie i zmiana nazw** — możliwość zaznaczenia wielu plików i wykonania operacji na całej grupie
- **Historia operacji i cofanie** — każda operacja (przeniesienie, zmiana nazwy, usunięcie) jest logowana z możliwością cofnięcia
- **Harmonogram automatycznego skanowania** — cykliczne skany dysku w tle bez ingerencji użytkownika

### Bezpieczeństwo i wielodostęp
- **Logowanie użytkowników** z rolami (Admin, Read-only) i sesjami JWT
- **Dziennik aktywności** — kto, kiedy i co zrobił z którym plikiem
- **HTTPS out-of-the-box** — wbudowana obsługa certyfikatów Let's Encrypt lub własnych

---

## 💾 Backup — przenoszenie plików na NAS lub tworzenie kopii zapasowych

> Planowana funkcjonalność

DiskAssistent będzie umożliwiał tworzenie kopii zapasowych wybranych plików lub całych grup na sieciowe zasoby dyskowe (NAS) lub lokalny katalog docelowy.

### Jak to będzie działać

1. **Definiowanie miejsca docelowego** — użytkownik konfiguruje jeden lub więcej celów backupu:
   - ścieżka UNC do udziału sieciowego (np. `\\NAS\Backup\`)
   - lokalny folder na innym dysku (np. `D:\Backup\`)
   - przyszłościowo: integracja z chmurą (WebDAV, SFTP)

2. **Wybór zakresu** — backup można uruchomić dla:
   - pojedynczego pliku z poziomu modalu szczegółów
   - całej grupy (np. „zrób kopię gry `Minecraft`")
   - kategorii (np. „zarchiwizuj wszystkie Dokumenty")
   - plików ze znacznikiem `is_missing = false` (tylko te obecne na dysku)

3. **Tryby operacji**:
   - **Kopia** — plik pozostaje w oryginalnym miejscu, do celu trafia kopia
   - **Przeniesienie** — plik jest przenoszony do celu i oznaczany w bazie jako `moved_to_backup = true`
   - **Synchronizacja (mirror)** — porównanie po dacie i rozmiarze, kopiowane są tylko zmienione pliki

4. **Postęp i raport** — backup uruchamiany jest w tle (tak jak skanowanie), a jego postęp można śledzić w tym samym stylu co `rescan-all`, z podziałem na pliki skopiowane / pominięte / błędne

5. **Weryfikacja integralności** — opcjonalne porównanie SHA-256 oryginału i kopii po zakończeniu transferu

### Planowane API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/backup/targets` | Lista skonfigurowanych celów backupu |
| `POST` | `/api/backup/targets` | Dodaj nowy cel (ścieżka UNC, folder, SFTP) |
| `POST` | `/api/backup/start` | Uruchom backup dla wybranego zakresu |
| `GET` | `/api/backup/status/{job_id}` | Śledź postęp zadania backupu |
| `GET` | `/api/backup/history` | Historia wykonanych kopii zapasowych |

### Wymagania środowiskowe

- Dostęp do udziału sieciowego musi być zamontowany w systemie operacyjnym lub podany jako ścieżka UNC dostępna z konta uruchamiającego serwer
- Dla SFTP planowana jest opcjonalna zależność: `paramiko`
