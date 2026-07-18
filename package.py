"""Build a shareable bundle of Case Companion for a non-technical recipient.

Produces dist/CaseCompanion/ containing:
  - the app code, corpus, and a PREBUILT corpus database (no build step needed)
  - setup.bat  (double-click once, with internet, to install Python deps + models)
  - start.bat  (double-click to run the app and open the browser)
  - HOW_TO_RUN.txt (plain-English instructions)

Then zips it to dist/CaseCompanion.zip.

Run:  python package.py

The recipient still needs Ollama installed (setup.bat links to it) and internet
for the one-time model download. After that, the app runs fully offline.
"""
import os
import shutil
import zipfile

ROOT = os.path.abspath(os.path.dirname(__file__))
DIST = os.path.join(ROOT, "dist")
BUNDLE = os.path.join(DIST, "CaseCompanion")

# What to copy into the bundle. Directories are copied whole.
INCLUDE_DIRS = ["app", "web", "corpus", "scripts", "samples"]
INCLUDE_FILES = ["config.py", "requirements.txt", "README.md"]

# The prebuilt corpus DB (already contains embeddings, so the recipient never
# has to run build_corpus.py, which would require Ollama during setup).
PREBUILT_DB = os.path.join(ROOT, "data", "case_companion.db")


def clean():
    if os.path.exists(BUNDLE):
        shutil.rmtree(BUNDLE)
    os.makedirs(BUNDLE)


def copy_code():
    for d in INCLUDE_DIRS:
        src = os.path.join(ROOT, d)
        if os.path.isdir(src):
            shutil.copytree(
                src, os.path.join(BUNDLE, d),
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
    for f in INCLUDE_FILES:
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(BUNDLE, f))


def copy_prebuilt_db():
    data_dir = os.path.join(BUNDLE, "data")
    os.makedirs(data_dir, exist_ok=True)
    if os.path.isfile(PREBUILT_DB):
        shutil.copy2(PREBUILT_DB, os.path.join(data_dir, "case_companion.db"))
        print("included prebuilt corpus database")
    else:
        # No prebuilt DB: fall back to building on the recipient's machine.
        # Leave a marker so setup.bat knows to run build_corpus.py.
        open(os.path.join(data_dir, "NEEDS_BUILD"), "w").close()
        print("WARNING: no prebuilt DB found; recipient's setup will build it "
              "(requires Ollama running during setup)")


SETUP_BAT = r"""@echo off
REM ===== Case Companion one-time setup (needs internet) =====
echo.
echo Setting up Case Companion. This runs once and needs internet.
echo.

REM 1. Check Python
where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python is not installed.
  echo Install Python 3.11 from https://www.python.org/downloads/ then run setup again.
  pause
  exit /b 1
)

REM 2. Check Ollama
where ollama >nul 2>nul
if errorlevel 1 (
  echo ERROR: Ollama is not installed.
  echo Install it from https://ollama.com/download then run setup again.
  pause
  exit /b 1
)

REM 3. Create a local Python environment and install dependencies
echo Installing Python packages...
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

REM 4. Download the AI models (large, one-time)
echo.
echo Downloading the Gemma model (about 10 GB) and the search model.
echo This is the slow part. Grab a coffee.
ollama pull gemma4:latest
ollama pull nomic-embed-text

REM 5. Build the reference library only if a prebuilt one was not shipped
if exist data\NEEDS_BUILD (
  echo Building the reference library...
  python scripts\build_corpus.py
  del data\NEEDS_BUILD
)

echo.
echo Setup complete. Double-click start.bat to run Case Companion.
pause
"""

START_BAT = r"""@echo off
REM ===== Run Case Companion =====
where ollama >nul 2>nul
if errorlevel 1 (
  echo Ollama is not installed. Run setup.bat first.
  pause
  exit /b 1
)

REM Make sure Ollama is running in the background
start "" ollama serve

call .venv\Scripts\activate
echo Starting Case Companion...
start "" http://localhost:8000
python -m uvicorn app.main:app --port 8000
pause
"""

HOW_TO_RUN = """CASE COMPANION - How to run it

Case Companion explains your legal documents in plain English, on your own
computer. Nothing you upload ever leaves this machine.

------------------------------------------------------------
FIRST TIME (needs internet, do this once)
------------------------------------------------------------
1. Install Python 3.11:  https://www.python.org/downloads/
   (On the first install screen, tick "Add Python to PATH".)

2. Install Ollama:  https://ollama.com/download
   (This is what runs the AI on your machine.)

3. Double-click  setup.bat
   It installs everything and downloads the AI model (about 10 GB - this
   part is slow, one time only). Leave it running until it says
   "Setup complete."

------------------------------------------------------------
EVERY TIME AFTER THAT (no internet needed)
------------------------------------------------------------
1. Double-click  start.bat
2. Your browser opens to Case Companion.
3. Drag a legal document (PDF or text) onto the page, then ask questions.

The first question after starting is slow while the AI wakes up. After
that it is quick.

------------------------------------------------------------
IS IT REALLY PRIVATE?
------------------------------------------------------------
Yes. Once setup is done you can turn off your WiFi and it still works.
Your documents stay on your computer.
"""


def write_launchers():
    with open(os.path.join(BUNDLE, "setup.bat"), "w", newline="\r\n") as f:
        f.write(SETUP_BAT)
    with open(os.path.join(BUNDLE, "start.bat"), "w", newline="\r\n") as f:
        f.write(START_BAT)
    with open(os.path.join(BUNDLE, "HOW_TO_RUN.txt"), "w", newline="\r\n") as f:
        f.write(HOW_TO_RUN)


def make_zip():
    zip_path = os.path.join(DIST, "CaseCompanion.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, _, filenames in os.walk(BUNDLE):
            for name in filenames:
                full = os.path.join(dirpath, name)
                arc = os.path.relpath(full, DIST)
                z.write(full, arc)
    size_mb = os.path.getsize(zip_path) / 1_000_000
    print(f"created {zip_path}  ({size_mb:.1f} MB)")


def main():
    clean()
    copy_code()
    copy_prebuilt_db()
    write_launchers()
    make_zip()
    print("\nDone. Send dist/CaseCompanion.zip to your recipient.")
    print("They unzip it, run setup.bat once (with internet), then start.bat.")


if __name__ == "__main__":
    main()
