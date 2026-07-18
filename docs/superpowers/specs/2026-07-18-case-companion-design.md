# Case Companion — Design Spec

**Date:** 2026-07-18
**Hackathon:** JustBuild "Build with Gemma" — Track 1: On-Device AI with Gemma 4
**Team goal:** Win Track 1 ($750 first / $250 second)

## One-line pitch

A private, offline legal assistant that explains a person's legal documents and rights
in plain English, grounded in a bundled corpus with citations — running entirely
on-device via Gemma 4, working with the network disabled.

## The user & the problem

**User:** an individual navigating their own legal case who can't easily afford or reach a
lawyer.

**Domain focus (intentionally narrow):** **family-law cases** and **cases where an
individual is suing the state.** Narrowing to these two lanes makes the user specific
(scores on Value), keeps the bundled "know your rights" corpus tractable, and targets
exactly the high-anxiety, can't-afford-a-lawyer situations the pitch is built for. Both are
high-stakes areas, which makes the safety features (#2 guardrail, disclaimer, risk flags)
score-earning rather than optional.

**Problem:** legal documents are frightening and opaque. People in legal trouble may lack
reliable internet, can't afford counsel, and shouldn't have to hand a personal legal
situation to a cloud company just to understand it.

**Why on-device (the rubric-winning angle):** access + dignity + zero cost + works
anywhere, offline, forever. The data used is public-record case data (retrievable by case
number), so the justification is **accessibility**, not secrecy. On-device is central to
the product, not incidental.

## The demo money-shot (build priority order)

1. User **uploads the legal document** they received (PDF-with-text or plain text).
2. App explains it **in plain English** and surfaces the user's **rights and likely next
   steps**, grounded in a bundled corpus, showing **citations** (which source each claim
   came from).
3. **Network disabled, ask a follow-up — it still works.** This single beat satisfies the
   eligibility gate (Gemma inference entirely on-device, verified network-off) and the
   privacy/access pitch simultaneously.

The success criterion demonstrated live: *upload → cited plain-English explanation →
WiFi-off follow-up answer.*

## Feature enhancements (in scope)

1. **Clickable citations that reveal the source snippet.** Each answer's citation shows the
   exact retrieved text it came from ("this came from §4 of your notice"). Biggest trust
   boost for a legal tool; cheap on top of RAG.

2. **Honesty / "I don't know" guardrail.** When retrieval finds nothing relevant (score
   below a threshold), the app says *"I don't have information about that in your
   documents"* instead of hallucinating. Directly scores on Evidence & Evaluation and is
   the responsible behavior for a legal context.

3. **Key-facts card on upload.** Immediately after upload (before chat), show a card
   extracting: **deadline / who vs. whom / amount / what's demanded / days to respond.**
   One structured Gemma call. This is the emotional payoff — the scary letter demystified
   at a glance.

   **3a. Draft-to-lawyer handoff.** A button on the key-facts card / chat that generates a
   **pre-filled message** to the client's lawyer ("Your client has a question about
   [key fact]: '[question]'"). The app **drafts only — it never sends** (opens `mailto:` or
   saves/copies the text). This preserves the 100% on-device guarantee: the draft is
   produced offline; the user sends it later when online. Demoed network-off.

4. **Live "network off" choreography.** Physically toggle airplane mode on-stage mid-demo.
   Not code — the moment that proves the eligibility gate and wins the track.

7. **Multi-language answers.** The assistant can explain in a second language, aligned with
   the accessibility pitch. **Demoed with Spanish**, English as fallback. Guardrail: verify
   quality on the chosen model before relying on it live; smaller Gemma models vary per
   language.

8. **Case-risk flags.** Extending the key-facts card, the app surfaces risks to the user's
   case in plain English — e.g. "only 5 days left to respond," "missing this deadline could
   result in a default judgment," "you may be waiving a right by signing this." Scoped to
   the two focus domains (family law, suing the state). Always paired with the
   **"not legal advice"** disclaimer and the #2 guardrail so it never overstates certainty.

9. **Case timeline (lightweight, read-only).** A chronological view merging two event
   types:
   - **App events** — "you uploaded *Notice of Hearing*" with a **local-clock** timestamp
     stored in SQLite (no network; fully offline).
   - **Extracted case events** — legal milestones Gemma pulls from the uploaded documents
     ("hearing Aug 3," "response due July 25"), reusing the key-facts/#8 extraction. Shown
     as "from your document" and user-confirmable, not presented as authoritative.

   Auto-populates from uploads + extraction. **No manual event editor, no reminders /
   notifications, no calendar sync** (out of scope). Supporting context, not the money-shot;
   sits low in the build priority.

## Architecture

Single local machine. Nothing crosses a network.

```
Client's computer (network can be OFF)

  Web UI (browser, localhost)  <-->  Python backend (RAG engine)  <-->  Ollama + Gemma 4
                                              |
                                     SQLite file: corpus + vector index
                                     (the "shareable bundle")
```

- **Web UI:** single clean page served from localhost — upload a document, ask questions,
  see answers with citations. Browser is a render surface only; fully local.
- **Python backend (RAG engine):** parse document -> chunk -> embed -> retrieve relevant
  snippets -> build prompt -> call Ollama -> return answer + the sources it used.
- **Ollama + Gemma 4:** local inference AND local embeddings. Model warmed on startup;
  responses streamed to the UI.
- **SQLite file:** the bundled "know your rights" + case-record corpus plus its vector
  index. This file IS the shareable bundle a lawyer/legal-aid org would ship to a client.

## Data flow

1. **Corpus prep (offline, once):** the reference corpus (know-your-rights content +
   case-record text) is parsed, chunked, embedded via Ollama, and stored in SQLite. Ships
   as the bundle.
2. **User uploads a document:** parsed (PDF-with-text / plain text), chunked, embedded, and
   added to the local index for this session.
3. **User asks a question (or "explain this document"):** the query is embedded, the top-k
   relevant chunks are retrieved from the corpus + uploaded doc, a grounded prompt is
   assembled, Gemma answers with citations back to the retrieved sources.

## Scope guardrails (YAGNI)

- **Formats:** PDF-with-selectable-text and plain text only. **No OCR** (scanned PDFs
  pre-converted by hand if needed for the demo).
- **Single machine.** No real cross-machine installer — the "lawyer packages -> client
  installs" story is told as narrative, not built.
- **Case timeline:** lightweight, read-only, auto-populated (see feature #9). No manual
  editor / reminders / calendar sync. The explainer is the star.
- **No cross-client comparison** (a client has only their own case).
- **No accounts, no servers, no cloud, no telemetry.**
- **Scoped to family law + suing-the-state only** — not general-purpose legal coverage.
- **Always shows a "not legal advice" disclaimer** — required given the high-stakes domain.
- **Draft-to-lawyer never auto-sends** — drafting only, to preserve the offline guarantee.
- **Multi-language:** one demo language (Spanish) + English fallback only; not open-ended
  localization.

## Latency plan

Bottleneck is Gemma inference (model size + machine), not the app language.

- Prefer the **smallest model that gives acceptable quality** (2B/4B) for the demo; use the
  bigger model on the teammate's machine only if quality demands it.
- **Warm the model** with a startup call so the first real question is fast.
- **RAG keeps prompts short** (only relevant snippets in context) -> faster answers.
- **Stream tokens** so responses feel instant.

## Rubric mapping (100 pts)

- **Value (25):** sympathetic, identified user; real accessibility problem.
- **Inputs & Data (15):** public-record provenance is clear; offline handling.
- **Enablement & Ease of Use (20):** clean client-facing UI, usable without a developer.
- **Underlying Model (20):** Gemma on-device is central; demonstrated network-off.
- **Evidence & Evaluation (20):** the upload -> cited-explanation -> WiFi-off sequence is a
  defined, live-demonstrated success criterion; the "I don't know" guardrail shows
  responsible, evaluated behavior.

## Build priority (so the demo survives a time crunch)

Core (must have): upload -> RAG Q&A with citations -> network-off, scoped to the two focus
domains, with the "not legal advice" disclaimer. Then, in order: key-facts card (#3),
clickable source snippets (#1), "I don't know" guardrail (#2), case-risk flags (#8),
timeline (#9), draft-to-lawyer (#3a), Spanish (#7). Each is additive and can be cut from
the bottom without breaking the core demo.

## Open items (non-blocking)

- Corpus size unknown until real data arrives; only tunes chunk/retrieve params, not the
  architecture.
- Confirm demo data is safe to show judges (public record -> low risk) and have a one-line
  provenance answer ready.

## Submission checklist (from hackathon rules)

- New, public GitHub repo created after kickoff, clean commit history.
- Kaggle writeup due Sat 3:00 PM MDT.
- 3-minute live demo, real product running, no slides.
