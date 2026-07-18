# Standalone executable distribution, Windows + macOS (UI + storage preserved)

Date: 2026-07-18

## Problem

Sharing Case Companion today (`package.py`) ships the source code plus `.bat`
launchers. The recipient must install Python, create a venv, and run the app
from source. We want to share something that runs without depending on the
source code: the recipient installs Ollama + pulls Gemma, then double-clicks a
single executable. This must work on **both Windows and macOS**.

The two things that must be preserved: the **web UI** and the **per-case
storage** (uploads, timeline, questions, obligations). This rules out an
Ollama-only / Modelfile approach, which has neither. The answer is a standalone
executable (PyInstaller) that carries the FastAPI server, the `web/` UI, and
SQLite storage inside it: a `CaseCompanion.exe` on Windows and a
`CaseCompanion.app` bundle on macOS.

## Build constraint: no cross-compilation

PyInstaller cannot cross-compile. A macOS `.app` must be built on macOS; a
Windows `.exe` must be built on Windows. There is no way around this in the
tooling. Decision: the Windows build is produced on this Windows machine, and
the macOS build is produced on a Mac the author has access to. Both use the same
cross-platform `build_exe.py`; each run targets the OS it runs on.

## Recipient prerequisites

- Ollama installed, with `gemma4:latest` (and `nomic-embed-text`) already
  pulled. Confirmed: recipients will have both.
- No Python, no source, no venv.

The executable does not bundle the model weights (~10 GB); that stays Ollama's job.
"Runs from the model" means Ollama + Gemma is the only prerequisite, and Python
/ source go away.

## Core problem: paths under a frozen executable

Two path assumptions break when frozen by PyInstaller:

1. **`web/` assets** - `app/main.py` references `"web"` relative to the current
   working directory (`app.mount("/web", StaticFiles(directory="web"))` and
   `FileResponse("web/index.html")`). When frozen, bundled read-only assets live
   under the temp extraction dir `sys._MEIPASS`, not the CWD.
2. **Storage DB** - `config.DB_PATH = "data/case_companion.db"` is CWD-relative.
   When frozen it must NOT live in the temp extraction dir (wiped on exit). The
   recipient's real case data must persist in a stable, writable, per-user
   location. On macOS this is especially important: writing inside the `.app`
   bundle is wrong (bundles are treated as read-only and may be relocated), so
   storage goes to a per-user application-data directory.

## Design

### 1. Path helpers (`config.py`)

- `resource_path(*parts)` - for read-only bundled assets. Returns a path under
  `sys._MEIPASS` when frozen (`getattr(sys, "frozen", False)`), else under the
  source root. Same on both OSes. Used for `web/`, `corpus/`, and the prebuilt
  corpus DB.
- `data_dir()` - for writable, per-user storage. Platform-specific when frozen:
  - **Windows**: `%LOCALAPPDATA%\CaseCompanion` (e.g. `C:\Users\<u>\AppData\Local\CaseCompanion`).
  - **macOS**: `~/Library/Application Support/CaseCompanion`.
  - **Dev (not frozen)**: `data/` in the source root, unchanged.

  Chosen over "next to the executable" because a macOS `.app` must not write
  inside its own bundle, and per-user app-data dirs are the platform-correct home
  for user data on both OSes. `DB_PATH` derives from `data_dir()`.

Keeping asset resolution and writable-storage resolution as two distinct helpers
is the whole point: assets are read-only and ephemeral under the frozen app;
storage must persist in a per-user location.

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

One cross-platform script; behavior branches on the host OS (`sys.platform`).

- Freeze `app.main` (uvicorn entry point).
  - **Windows**: onefile `CaseCompanion.exe`.
  - **macOS**: a `CaseCompanion.app` bundle (`--windowed`, with a bundle
    identifier). A onedir-style `.app` is the standard Mac form.
- Bundle as data files (both OSes): `web/`, `corpus/`, and the prebuilt corpus DB
  (`data/case_companion.db`).
- Entry point starts uvicorn on port 8000 and opens the browser to
  `http://localhost:8000`.
- Hidden-import / collect any uvicorn/fastapi/starlette submodules PyInstaller
  misses (same set on both OSes).

### 5. Update `package.py`

Package whichever build exists for the host OS into a shareable zip:

- **Windows**: `CaseCompanion.exe` + `HOW_TO_RUN.txt` -> `dist/CaseCompanion-windows.zip`.
- **macOS**: `CaseCompanion.app` + `HOW_TO_RUN.txt` -> `dist/CaseCompanion-macos.zip`.

`HOW_TO_RUN.txt` states the single prerequisite (Ollama + pulled models) and, on
macOS, the Gatekeeper first-open step (right-click -> Open). Drop the old source
bundle, `setup.bat`, and `start.bat`.

## Trade-offs / honest notes

- **No cross-compilation**: the Mac build must be produced on a Mac, the Windows
  build on Windows. Two separate build runs, one per OS.
- **macOS Gatekeeper**: an unsigned, un-notarized `.app` is blocked by default on
  modern macOS; the recipient must right-click -> Open the first time (documented
  in HOW_TO_RUN). Proper fix is an Apple Developer ID + notarization ($99/yr),
  out of scope for now.
- **macOS architecture**: the `.app` targets the arch of the build Mac (Apple
  Silicon arm64 unless built on / for Intel). An arm64 build does not run
  natively on Intel Macs. Universal2 is possible later but needs a universal
  Python; out of scope for now. The build targets the author's Mac arch and this
  limitation is noted to recipients.
- **Windows SmartScreen**: unsigned `.exe` may show an "unknown publisher"
  warning; the recipient clicks "More info -> Run anyway".
- The artifact is large-ish (frozen Python, ~50-150 MB), far smaller than the
  model. Ollama + Gemma remain a hard prerequisite (where the model runs).
- The frozen app still contains the code, just invisible to the user. "Not
  depending on the code" means the recipient never touches Python or source.

## Verification

- **Dev run unchanged (both OSes)**: `python -m uvicorn app.main:app` still
  serves the UI and reads/writes `data/case_companion.db` (path helpers resolve
  to source paths when not frozen).
- **Frozen Windows run**: build the exe, run on a machine with Ollama + Gemma,
  confirm the UI loads, a document uploads, and the DB is created under
  `%LOCALAPPDATA%\CaseCompanion` and survives a restart.
- **Frozen macOS run**: build the `.app` on the Mac, run it (right-click -> Open
  the first time), confirm the UI loads, a document uploads, and the DB is
  created under `~/Library/Application Support/CaseCompanion` and survives a
  restart.
- **First-run seeding (both OSes)**: delete the writable DB, launch, confirm the
  corpus is present (reference answers work) and a new case can be created.
