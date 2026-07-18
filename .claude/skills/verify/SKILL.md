---
name: verify
description: How to build, launch, and drive Case Companion for end-to-end verification.
---

# Verifying Case Companion

Launch (needs Ollama running locally with `gemma4:latest` + `nomic-embed-text`):

    .venv/bin/python -m uvicorn app.main:app --port 8000

The user often keeps their own server on port 8000 — check `lsof -i :8000` first
and use a scratch port (e.g. 8077) for smoke tests unless the task is about the
live server. First LLM call after startup is slow (model load).

Drive the surfaces:

- Upload (full pipeline: classify, events, deadlines, faults):
  `curl -F "file=@samples/notice_of_hearing.txt" http://localhost:PORT/api/upload`
- Q&A: POST `/api/ask` `{"question": "..."}` — check `grounded` + `sources`.
- Timeline `/api/timeline`, warnings `/api/warnings`, questions `/api/questions`.
- Second opinion: POST `/api/check-advice` `{"text": "..."}` (several LLM calls, slow).
- CLIs: `scripts/verify_draft.py`, `scripts/build_filing_docx.py`,
  `scripts/process_intake.py`, `scripts/extract_deadline_rules.py`,
  `scripts/import_authorities.py` — all print evidence and exit nonzero on failure.

Gotchas:

- **Every upload writes real rows** (chunks, timeline, obligations, questions) into
  `data/case_companion.db`. Clean up probe rows afterward by id/source — do NOT
  bulk-delete tables; the DB holds the user's real case data and the imported
  1,311-authority library.
- `scripts/build_corpus.py` is NOT idempotent — re-running duplicates corpus
  chunks. Clear `kind='corpus'` chunks first.
- Tests (`.venv/bin/python -m pytest tests -q`) are all offline (LLM calls are
  monkeypatched) — they are CI, not verification.
- Model outputs vary run to run: classification of ambiguous docs and event
  extraction are nondeterministic; deterministic layers (content-signal
  classification, deadline math, verifier) are the stable things to assert on.
