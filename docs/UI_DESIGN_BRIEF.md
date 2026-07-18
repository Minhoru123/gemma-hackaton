# Case Companion — UI Design Brief

Brief for redesigning the web interface of Case Companion. Everything described
here is already built and working behind a functional-but-plain single-page UI;
the task is to design the interface it deserves.

## What the product is

Case Companion is an **on-device legal assistant** for people navigating a
court case — primarily self-represented litigants, or people who have a lawyer
but want to stay oriented and prepared. The user uploads their case documents
(motions, orders, notices, letters) and the app:

- explains documents in **plain English (or Spanish)**, with citations back to
  the exact source text,
- builds a **case timeline** from every dated event found in the documents,
- computes **presumptive deadlines** ("a motion was filed → an opposition is
  presumptively due in 14 days"),
- tracks **open obligations** and warns when something is overdue or due soon,
- **flags fault language** in documents (missed deadlines, waived arguments,
  sanctions…) and turns each flag into a question for the user's attorney,
- gives a **second opinion** on advice the user was given: each claim is
  checked against the captured text of their documents and authorities.

Everything runs locally: a FastAPI backend on `localhost:8000`, Gemma 4 via
Ollama for generation, local embeddings, SQLite storage. **Nothing ever leaves
the user's machine** — that privacy guarantee is the core of the product and
should be felt in the design.

## Who the user is

Someone in a stressful, high-stakes situation who is *not* a lawyer. They may
have just received a document they don't understand ("Notice of Hearing",
"Order to Show Cause"). Assume anxiety, low legal literacy, and possibly low
technical literacy. The UI's job is to demystify and orient, never to
overwhelm. It must work in English and Spanish (language switcher exists).

## Design principles (non-negotiable, from the product's ethics)

1. **Information, not advice.** The app never says "you should…" or judges
   whether a lawyer is right. It reports what the documents say, with quotes.
   The footer disclaimer ("This is general information, not legal advice")
   must stay prominent.
2. **Everything is cited.** Answers carry citations to source chunks; fault
   flags carry the verbatim sentence they came from; second-opinion results
   quote the text they matched. Citations/quotes need first-class visual
   treatment — they are the trust mechanism.
3. **Presumptive vs. confirmed.** Computed deadlines are always labeled
   *presumptive — confirm with the court or your attorney*. The visual
   language must keep this distinction impossible to miss (confirmed = solid,
   presumptive = clearly provisional).
4. **Private and offline.** There's a network indicator showing the app is
   running offline/on-device. Make this a visible badge of honor, not a
   status-bar afterthought.
5. **Calm, not alarmist.** Warnings are sorted overdue → due soon → open and
   should create urgency without panic.

## Current UI inventory (what exists today)

Single page, two columns, vanilla HTML/CSS/JS (`web/index.html`, `web/app.js`,
`web/style.css`):

- **Header:** title, language selector (English/Spanish), network-status
  indicator.
- **Left column:**
  - Drop zone: "Drop a PDF or text file, or click to choose" (.pdf/.txt/.md).
  - Warnings card (open obligations, overdue first; items can be marked done).
  - Key-facts card (shown after upload: doc type, dates, deadline).
  - Timeline card (all events, chronological).
- **Right column:**
  - Chat: question input + answers with citations.
  - "Ask your attorney" questions card (add / check off items).
  - Second-opinion card: textarea to paste advice, "Check against captured
    text" button, results listed as *matches / conflicts with / not covered
    by* with quoted text.
- **Footer:** disclaimer.

## Backend API (already implemented — design around these flows)

| Endpoint | Purpose |
|---|---|
| `POST /api/upload` | Upload a document. Returns key facts, detected doc type, filed date, events added, presumptive deadlines created, obligations auto-satisfied, and fault flags — a lot happens on upload and the UI must narrate it. |
| `POST /api/ask` | Ask a question; returns answer + cited source chunks. Below a confidence threshold it answers "I don't know" rather than guessing — that state needs design. |
| `GET /api/timeline` | All timeline events (filings, case events, deadlines). |
| `GET /api/warnings` | Open obligations, sorted overdue → due soon → open. |
| `POST /api/obligations/satisfy` | Mark an obligation done. |
| `GET /api/questions`, `POST /api/questions/add`, `POST /api/questions/resolve` | The ask-your-attorney list. |
| `POST /api/check-advice` | Second-opinion check on pasted advice. |

## Key moments to design

1. **First open / empty state.** No documents yet. The app should invite the
   first upload and explain what it will do, without a wall of text.
2. **The upload moment.** One upload triggers a cascade: doc classified,
   events extracted, deadlines computed, obligations satisfied, faults
   flagged. Today this is a terse summary; it deserves a designed "here's
   what I found in this document" reveal.
3. **Asking a question.** Local inference is slow (up to ~1–2 minutes on a
   modest machine; the first question after startup is slowest while the
   model loads). Design an honest, calming loading state — no fake progress.
   Answers include citations the user can inspect.
4. **The "I don't know" answer.** When retrieval confidence is low the app
   declines to answer. This should read as trustworthy, not broken.
5. **Timeline + deadlines.** Chronological view mixing past events and
   upcoming (presumptive) deadlines. The presumptive label and "confirm with
   your attorney" nudge must travel with each computed date.
6. **Warnings.** Overdue / due-soon / open, glanceable at app open.
7. **Ask-your-attorney list.** A running checklist; items arrive from
   watchdog flags, advice-check mismatches, and manual adds; checked off once
   asked.
8. **Second opinion.** Paste → per-claim verdicts (*matches / conflicts /
   not covered*), each with the quoted text. Must visually avoid implying
   "your lawyer is wrong" — mismatches become questions to ask, not verdicts.

## Hard constraints

- **Fully offline:** no CDN assets, no web fonts, no external images or
  analytics. Everything ships in the repo (system font stack or bundled
  fonts).
- **Stack:** single page served by FastAPI from `web/`; plain HTML/CSS/JS
  today. A redesign should stay framework-light (no build step preferred).
- **Localhost app:** desktop browser is the primary target; should remain
  usable at laptop sizes (~1280px) down to a narrow window. Mobile is
  secondary.
- **Bilingual:** all UI copy must have an English and Spanish variant;
  layouts must tolerate longer Spanish strings.
- **Accessibility:** the audience skews non-technical and stressed — large
  readable type, clear hierarchy, honest states, WCAG AA contrast.

## Deliverables wanted from this design pass

1. Overall layout / information architecture (does the two-column split
   survive? is the timeline a first-class view?).
2. Visual system: palette, type scale, spacing, card/citation/quote
   treatments, presumptive-vs-confirmed and warning-severity semantics —
   all workable in light form at minimum (dark mode welcome).
3. Designed states for the eight key moments above, including loading,
   empty, and error states.
4. Copy tone guidance consistent with the principles (calm, plain-language,
   never advisory).
