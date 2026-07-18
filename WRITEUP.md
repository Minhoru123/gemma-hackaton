# Case Companion — Frontier Legal Help That Never Leaves Your Laptop

**Subtitle:** An offline, private legal-document assistant powered by Gemma 4, for people
navigating their own family-law or suing-the-state case without a lawyer.

**Track:** Edge / On-Device

---

## The problem

People handling their own legal case often can't afford a lawyer at all times for questions, may not have reliable
internet, and shouldn't have to hand their most personal situation to a cloud AI chatbot especially when it comes to confidential documents.
Court filings are public record, so the barrier isn't secrecy, it's access, dignity, and
plain-English understanding. Case Companion explains a person's documents and their rights,
with citations, on any laptop, offline, for free.

## Architecture

A Python / FastAPI backend serves a local web UI at `localhost`; Gemma 4 runs via Ollama,
with `nomic-embed-text` for embeddings. Everything is local — the only outbound call the app
ever makes is to Ollama on `127.0.0.1`.

**Understanding a document (RAG core).** A user uploads a legal document. It's chunked and
embedded into a local SQLite store — which doubles as the shareable "bundle" a legal-aid org
can hand to a client. Questions run a retrieval loop: fetch top-k chunks, gate on a
similarity threshold, and have Gemma 4 answer *only* from that context, citing sources as
`[Source N]`. Below the threshold, it returns "I don't have that information" rather than
inventing legal facts. Every answer shows its receipts: click a citation to reveal the exact
source snippet.

**Case-watch layer.** Each upload is analyzed by document *behavior*, not title: operative
language ("IT IS HEREBY ORDERED", "moves this court for") is checked deterministically and
overrides the model, so a mislabeled filing is still classified correctly. From that, the
app builds a case timeline, computes clearly-labeled *presumptive* deadlines from an editable
rules table, opens obligations (a to-do list that auto-satisfies when the awaited document is
uploaded), and runs a watchdog that flags language attributing a missed deadline or waived
argument to a party — always with the exact quote, never a verdict.

## Verified legal drafting (technical depth)

Beyond Q&A, the repo includes mechanical, fully-offline tooling that enforces one rule:
**nothing uncaptured goes into a draft.** All of it is pure Python and covered by tests.

- **Authorities library.** Every citable authority is a row in SQLite with captured full
  text and provenance. Web-sourced rows stay non-citable until a human signs off.
- **Draft verification** (`verify_draft.py`). Before filing, it checks that every citation
  resolves to a *confirmed* authority (with citation-form canonicalization), every 15+
  character quotation matches the source verbatim (ellipsis- and bracket-tolerant), and no
  unresolved `[[MARKER]]` remains. It exits nonzero, so it can gate a build.
- **Intake & coverage maps.** Filings dropped into `intake/` are scanned for citations and
  unknowns are queued for capture; coverage maps track whether a responsive draft answers
  every contention in an opposing filing.
- **Filing builder** (`build_filing_docx.py`). Produces a court-ready `.docx` (two-column
  caption, Times New Roman 13pt, double-spaced); any unresolved marker renders bold-on-yellow
  so it can't be missed.
- **Second opinion.** Paste a lawyer's advice; each checkable claim is compared against
  captured corpus, case documents, and authorities, and reported as *matches / conflicts with
  / not covered by* — with the text quoted. It never says the lawyer is right or wrong;
  conflicts become "ask your attorney" questions.

## How we used Gemma 4

Gemma 4 (`gemma4:latest` via Ollama) is the core reasoning engine. It generates the
plain-English, cited answers; extracts key facts (parties, deadline, action required, risk
flags) from an uploaded document; and assists document classification. We run it with
`think:false` to disable chain-of-thought and return clean final answers. The deterministic
layers (operative-language classification, quote verification, deadline rules) wrap the model
so its output is grounded and checkable rather than trusted blindly.

## Challenges we overcame

- **Provable offline eligibility.** We wrote `offline_check.py`, which scans the entire repo
  and fails if any non-local URL or networking import exists outside the sanctioned Ollama
  client. "It's really offline" is demonstrable, not just claimed.
- **Reasoning-model scaffolding leak.** Some Gemma builds leaked `<|channel|>thought` text
  into answers. We fixed it with `think:false` plus a strip fallback.
- **Hallucination guardrail.** We tuned the retrieval-score threshold against real queries
  (relevant questions score 0.62–0.84, off-topic 0.36–0.46) so off-topic questions get an
  honest "I don't know."
- **Trust in a high-stakes domain.** Every generated deadline is labeled *presumptive*, every
  answer carries a "general information, not legal advice" disclaimer, and the watchdog and
  second-opinion features report signals with quotes instead of issuing verdicts.

## The demo (offline money shot)

Upload a notice of hearing → the Key Facts card fills in with a red risk flag → ask "What
happens if I miss the deadline?" and get a cited answer → ask an off-topic question and get
an honest "I don't know" → switch to Spanish → then **turn off WiFi and ask again.** It still
answers. Gemma 4 is running entirely on the machine. No network, no per-token bill, no data
leaving the device.
