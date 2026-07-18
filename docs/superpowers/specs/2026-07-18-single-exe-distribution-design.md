# Single-exe distribution (UI + storage preserved)

Date: 2026-07-18

## Problem

Sharing Case Companion today (`package.py`) ships the source code plus `.bat`
launchers. The recipient must install Python, create a venv, and run the app
from source. We want to share something that runs without depending on the
source code: the recipient installs Ollama + pulls Gemma, then double-clicks a
single executable.

The two things that must be preserved: the **web UI** and the **per-case
storage** (uploads, timeline, questions, obligations). This rules out an
Ollama-only / Modelfile approach, which has neither. The answer is a single
standalone Windows executable (PyInstaller onefile) that carries the FastAPI
server, the `web/` UI, and SQLite storage inside it.

## Recipient prerequisites

- Ollama installed, with `gemma4:latest` (and `nomic-embed-text`) already
  pulled. Confirmed: recipients will have both.
- No Python, no source, no venv.

The exe does not bundle the model weights (~10 GB); that stays Ollama's job.
"Runs from the model" means Ollama + Gemma is the only prerequisite, and Python
/ source go away.

## Core problem: paths under a frozen exe

Two path assumptions break when frozen into a PyInstaller onefile exe:

1. **`web/` assets** - `app/main.py` references `"web"` relative to the current
   working directory (`app.mount("/web", StaticFiles(directory="web"))` and
   `FileResponse("web/index.html")`). In a onefile exe, bundled read-only assets
   live under the temp extraction dir `sys._MEIPASS`, not the CWD.
2. **Storage DB** - `config.DB_PATH = "data/case_companion.db"` is CWD-relative.
   Under a onefile exe it must NOT live in the temp extraction dir (wiped on
   exit). The recipient's real case data must persist in a stable, writable
   location next to the exe.

## Design

### 1. Path helpers (`config.py`)

- `resource_path(*parts)` - for read-only bundled assets. Returns a path under
  `sys._MEIPASS` when frozen (`getattr(sys, "frozen", False)`), else under the
  source root. Used for `web/`, `corpus/`, and the prebuilt corpus DB.
- `data_dir()` - for writable storage. Returns `dirname(sys.executable)/data`
  when frozen, else `data/` in dev. `DB_PATH` derives from `data_dir()`.

Keeping asset resolution and writable-storage resolution as two distinct helpers
is the whole point: assets are read-only and ephemeral under the exe; storage
must persist.

### 2. Fix asset paths (`app/main.py`)

`StaticFiles(directory=...)` and `FileResponse(...)` use `config.resource_path("web", ...)`
instead of the bare `"web"` string. No behavior change in dev (resolves to the
same source path).

### 3. First-run DB seeding

On startup, if the writable DB in `data_dir()` does not exist but a prebuilt
corpus DB is bundled, copy the prebuilt DB into `data_dir()` once. This gives the
recipient the reference library on first run; their case data then accumulates
in that same writable DB. If the writable DB already exists, do nothing (never
overwrite the recipient's data).

### 4. Build script (`build_exe.py` + PyInstaller spec)

- Freeze `app.main` (uvicorn entry point) into one exe.
- Bundle as data files: `web/`, `corpus/`, and the prebuilt corpus DB
  (`data/case_companion.db`).
- Entry point starts uvicorn on port 8000 and opens the browser to
  `http://localhost:8000` (same behavior as today's `start.bat`).
- Hidden-import / collect any uvicorn/fastapi submodules PyInstaller misses.

### 5. Update `package.py`

Ship `CaseCompanion.exe` + a revised `HOW_TO_RUN.txt` whose only prerequisite is
Ollama + the pulled models. Drop the source bundle, `setup.bat`, and
`start.bat`. Zip the exe + instructions to `dist/CaseCompanion.zip`.

## Trade-offs / honest notes

- The exe is large-ish (frozen Python, ~50-150 MB), far smaller than the model.
- Ollama + Gemma remain a hard prerequisite (where the model runs).
- The exe still contains the app code, just frozen and invisible to the user.
  "Not depending on the code" means the recipient never touches Python or
  source, not that the code ceases to exist.

## Verification

- Dev run unchanged: `python -m uvicorn app.main:app` still serves the UI and
  reads/writes `data/case_companion.db` (path helpers resolve to source paths
  when not frozen).
- Frozen run: build the exe, run it on a machine with Ollama + Gemma, confirm
  the UI loads, a document uploads, and the DB is created next to the exe and
  survives a restart.
- First-run seeding: delete the writable DB, launch, confirm the corpus is
  present (reference answers work) and a new case can be created.
