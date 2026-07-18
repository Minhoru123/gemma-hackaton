# Case Companion

On-device legal assistant (Gemma 4 via Ollama). Explains legal documents in plain
English with citations. Runs fully offline.

## Run

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    python scripts/build_corpus.py
    python -m uvicorn app.main:app --port 8000

Open http://localhost:8000

## Models

The app uses two local Ollama models, both fully offline:

- **Generation:** `gemma4:latest`
- **Embeddings:** `nomic-embed-text`

Make sure both are pulled before first run:

    ollama pull gemma4:latest
    ollama pull nomic-embed-text

The first question after startup is slower while the model loads into memory. Ask one
warm-up question before a demo so the model is hot.

## Drafting-discipline tooling

Beyond Q&A, the repo includes mechanical tooling for verified legal drafting. The rule
it enforces: **nothing uncaptured goes in a draft.** All of it is pure Python, fully
offline, and covered by `tests/`.

**Authorities library.** Every authority a draft may cite is a row in the `authorities`
table (same SQLite database), with captured full text and provenance. Rows without a
`confirmed_by` value are Tier 2 (web-sourced, awaiting sign-off) and are not citable.

    python scripts/add_authority.py --name "United States v. Salerno" \
        --citation "481 U.S. 739" --file salerno.txt --type case \
        --court "U.S. Supreme Court" --year 1987 \
        --source-url https://... --retrieved 2026-07-18 --confirmed-by David

**Draft verification.** Runs on every draft before filing; exits nonzero on any hard
failure so it can gate a build:

    python scripts/verify_draft.py draft.md [--coverage coverage_map.md]

Checks: every citation resolves to a *confirmed* library row (with citation-form
canonicalization); every quotation of 15+ characters matches the cited authorities'
captured text verbatim (ellipsis- and [bracket]-tolerant); no `[[MARKER]]` remains;
and, with `--coverage`, no contention in the coverage map is left unanswered.

**Intake lane.** Drop filings (yours or opposing) into `intake/`; each is scanned for
citations, diffed against the library, and unknowns are queued on
`data/FETCH_LIST.md` for capture. Processed files move to `intake/completed/`.

    python scripts/process_intake.py

**Coverage maps.** Seed a checklist of an opposing filing's contentions; check boxes
as the responsive draft answers them; verify with `--coverage`:

    python scripts/seed_coverage_map.py their_motion.pdf coverage_map.md

**Filing builder.** Builds a court-ready .docx (two-column caption, Times New Roman
13pt, double-spaced); unresolved `[[MARKERS]]` render bold-on-yellow:

    python scripts/build_filing_docx.py draft.md caption.json out.docx

`caption.json` keys: `court`, `plaintiff`, `defendant`, `case_no`, `judge`, `title`.

The recommended pipeline per document: draft → `verify_draft.py` (fix until clean) →
`build_filing_docx.py`. Deadlines are never computed by the system — they are entered
by a human. Currency/good-law checking is out of scope (offline by design).
