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

## Case-watch features

Everything below surfaces information to the user; the system never contacts
anyone on the user's behalf.

**Timeline.** Every upload is analyzed (document type, filed date, and all dated
events it mentions) and placed on the case timeline, alongside extracted
deadlines and presumptive deadlines. Documents are classified by what their
text *does*, not by their title or filename: operative language (e.g. "moves
this court for", "IT IS HEREBY ORDERED", "reply in support of") is checked
deterministically and overrides the model — a document titled "Notice of
Motion" that asks for relief is treated as a motion.

**Presumptive deadlines.** `deadline_rules.json` maps filing types to what they
trigger (e.g. a motion triggers an opposition in 14 days). Dates computed from
it are always labeled *presumptive — confirm with the court or your attorney*:
the count ignores service method, weekends, holidays, and local variations.
The shipped rules are EXAMPLES — edit the file and verify each period for your
court. Deadlines a human confirms directly are the authoritative ones.

To build the rules table from your court's actual rules, upload them (e.g. the
Utah Rules of Civil Procedure as PDF or text) to the extractor:

    python scripts/extract_deadline_rules.py urcp.pdf   # -> deadline_rules_proposed.json
    # review the proposed file: every rule carries the verbatim sentence it
    # came from — check the day counts and cites, edit or delete entries
    python scripts/extract_deadline_rules.py --approve  # merge into deadline_rules.json

Extraction is proposal-first (nothing activates without your approval) and
mechanically gated: any proposed rule whose quote does not verbatim-match the
source text is dropped automatically.

**Warnings & to-do.** Filings create open obligations (tracked in the database);
the Warnings panel shows what is still open, sorted overdue → due soon → open.
Uploading a document of the awaited type (e.g. an opposition) automatically
satisfies the matching obligation; anything can also be marked done by hand.
Warnings appear when the app is opened — nothing runs in the background.

**Watchdog.** Every uploaded document is scanned for language attributing an
error or missed obligation to a party or lawyer, across categories: untimely
filing, waived/forfeited arguments, missed hearings, discovery failures,
sanctions, failure to prosecute, defaults, blown limitations periods, and
unpreserved issues. Each hit is flagged with the exact sentence and routed to
the ask-your-attorney list — one question per fault. The system reports the
signal with the quote; it never issues a verdict about the lawyer.

**Ask your attorney.** A running list of things worth raising with counsel:
watchdog flags, advice-check mismatches, and questions the user adds. Items
are checked off once asked.

**Second opinion.** Paste advice from a lawyer into the Second Opinion panel.
Each checkable claim is compared against captured text (rights corpus,
uploaded case documents, captured authorities) and reported as *matches /
conflicts with / not covered by* the captured text, with the text quoted.
It deliberately never says the lawyer is right or wrong — conflicts and gaps
become ask-your-attorney questions instead. Capture the rules and authorities
for your case with `add_authority.py` (below) to make this check meaningful.

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

**Bulk import from an existing reference library.** If you maintain a library
elsewhere (an `AUTHORITIES.jsonl` index plus `_AI_TEXT/` captured full texts),
import the whole thing:

    python scripts/import_authorities.py "/path/to/_REFERENCE_LIBRARY"
        # --fresh          start over (clears the authorities tables first)
        # --embed-holdings also index each authority's holding for search /
        #                  the second-opinion check (needs Ollama)
        # --embed-rules    also index full statute/rule texts (slower)

Provenance is preserved: library-provenance rows import as citable; web-captured
rows keep their recorded confirmation or stay Tier 2. Compound citations
("262 U.S. 390 (1923); 43 S.Ct. 625") get an alias per component so a draft
citing either form resolves. A citation with several captures (statute
versions, history packets) keeps them all: display uses the most complete
text, and quote verification checks against every sibling. Re-running the
import is safe — rows replace by (citation, name).

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
