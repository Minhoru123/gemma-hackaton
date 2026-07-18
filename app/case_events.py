"""Per-document analysis on upload: classify the document by what it DOES
(operative language in the body — never the title or filename), find its filed
date, pull every dated event for the timeline, and flag language attributing
errors to a party or lawyer. Fault flags are signals routed to the
ask-your-attorney list, never verdicts."""

import re
from app import ollama_client, dates
from app.extract import _extract_json

DOC_TYPES = ["motion", "opposition", "reply", "order", "notice", "letter", "other"]

FAULT_CATEGORIES = [
    "untimely-filing",      # filed/served late, or not at all
    "waiver-forfeiture",    # argument waived or forfeited by not raising it
    "missed-hearing",       # failure to appear
    "discovery-failure",    # failure to respond to or supplement discovery
    "sanctions",            # sanctions imposed or threatened against a party/counsel
    "failure-to-prosecute", # case not moved forward
    "default",              # default or default judgment for non-response
    "limitations",          # statute of limitations / repose missed
    "preservation",         # issue not preserved for appeal
    "other-error",
]

# Deterministic content signals: operative language checked in priority order.
# A hit here overrides the model's classification — a document titled "Notice
# of Motion" that moves the court for relief IS a motion.
_CONTENT_SIGNALS = [
    ("order", r"\bit is (?:hereby |further )?ordered\b|\bso ordered\b|"
              r"\bthe court (?:hereby )?(?:orders|grants|denies)\b"),
    ("reply", r"\breply (?:memorandum )?in (?:further )?support of\b"),
    ("opposition", r"\b(?:memorandum|brief) in opposition to\b|"
                   r"\bopposition to (?:the |defendant'?s? |plaintiff'?s? )?motion\b|"
                   r"\bopposes? the motion\b"),
    ("motion", r"\bmoves? (?:this |the )?court\b|\bmoves? for\b|\bhereby moves\b"),
]

_PROMPT = (
    "Analyze this legal document. Classify it by what the text DOES, not by "
    "its title or caption: a document that asks the court for relief is a "
    "motion even if titled 'Notice'; a document containing the court's ruling "
    "is an order. Return ONLY a JSON object with keys:\n"
    "doc_type (one of: motion, opposition, reply, order, notice, letter, other),\n"
    "filed_date (the date this document was filed/issued, as YYYY-MM-DD, or \"\"),\n"
    "events (array of {{date: YYYY-MM-DD, event: short description}} for every "
    "dated thing the document says happened or will happen),\n"
    "faults (array with one entry for EACH place the document attributes an "
    "error, failure, or missed obligation to a party or lawyer — e.g. a late "
    "or missing filing, a waived argument, a missed hearing, unanswered "
    "discovery, sanctions, failure to prosecute, a default, a blown statute "
    "of limitations, or an unpreserved issue. Each entry: {{category: one of "
    f"{', '.join(FAULT_CATEGORIES)}; "
    "quote: the exact sentence; who: which party or lawyer; issue: short "
    "label}}. Empty array if none).\n\nDocument:\n\n{doc}"
)

def _valid_date(s: str) -> str:
    # Semantic validation: "2026-02-30" and month 13 are rejected, not just
    # malformed strings — a bad model date must never reach date arithmetic.
    return dates.valid_iso(s)


def classify_by_content(text: str) -> str:
    """Deterministic classification from operative language, '' if no signal."""
    for doc_type, pattern in _CONTENT_SIGNALS:
        if re.search(pattern, text, re.IGNORECASE):
            return doc_type
    return ""


def _valid_faults(data: dict) -> list[dict]:
    out = []
    raw = data.get("faults", [])
    for f in raw if isinstance(raw, list) else []:
        if not (isinstance(f, dict) and f.get("quote")):
            continue
        category = str(f.get("category", "")).strip().lower()
        if category not in FAULT_CATEGORIES:
            category = "other-error"
        out.append({"category": category, "quote": str(f["quote"]),
                    "who": str(f.get("who", "")), "issue": str(f.get("issue", ""))})
    return out


def analyze(document_text: str) -> dict:
    raw = ollama_client.generate(_PROMPT.format(doc=document_text[:12000]))
    data = _extract_json(raw)

    doc_type = str(data.get("doc_type", "")).strip().lower()
    if doc_type not in DOC_TYPES:
        doc_type = "other"
    # Operative language in the body beats the model's (title-influenced) call.
    doc_type = classify_by_content(document_text) or doc_type

    events = []
    for ev in data.get("events", []) if isinstance(data.get("events"), list) else []:
        if isinstance(ev, dict) and _valid_date(ev.get("date")) and ev.get("event"):
            events.append({"date": _valid_date(ev["date"]),
                           "event": str(ev["event"])})

    return {"doc_type": doc_type,
            "filed_date": _valid_date(data.get("filed_date")),
            "events": events, "faults": _valid_faults(data)}
