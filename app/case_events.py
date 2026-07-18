"""Per-document analysis on upload: classify the document, find its filed
date, pull every dated event for the timeline, and — for court orders — flag
language attributing fault for a procedural failure. The fault flag is a
signal routed to the ask-your-attorney list, never a verdict."""

import re
from app import ollama_client
from app.extract import _extract_json

DOC_TYPES = ["motion", "opposition", "reply", "order", "notice", "letter", "other"]

_PROMPT = (
    "Analyze this legal document. Return ONLY a JSON object with keys:\n"
    "doc_type (one of: motion, opposition, reply, order, notice, letter, other),\n"
    "filed_date (the date this document was filed/issued, as YYYY-MM-DD, or \"\"),\n"
    "events (array of {{date: YYYY-MM-DD, event: short description}} for every "
    "dated thing the document says happened or will happen),\n"
    "fault (object with found: true/false, quote: the exact sentence, who: which "
    "party or lawyer, issue: short label — set found true ONLY if the document "
    "attributes a procedural failure such as an untimely filing, a waived "
    "argument, or a missed response to someone).\n\nDocument:\n\n{doc}"
)

_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _valid_date(s: str) -> str:
    s = str(s or "").strip()
    return s if _ISO_RE.match(s) else ""


def analyze(document_text: str) -> dict:
    raw = ollama_client.generate(_PROMPT.format(doc=document_text[:6000]))
    data = _extract_json(raw)

    doc_type = str(data.get("doc_type", "")).strip().lower()
    if doc_type not in DOC_TYPES:
        doc_type = "other"

    events = []
    for ev in data.get("events", []) if isinstance(data.get("events"), list) else []:
        if isinstance(ev, dict) and _valid_date(ev.get("date")) and ev.get("event"):
            events.append({"date": _valid_date(ev["date"]),
                           "event": str(ev["event"])})

    fault_in = data.get("fault") if isinstance(data.get("fault"), dict) else {}
    fault = {"found": bool(fault_in.get("found")),
             "quote": str(fault_in.get("quote", "")),
             "who": str(fault_in.get("who", "")),
             "issue": str(fault_in.get("issue", ""))}

    return {"doc_type": doc_type,
            "filed_date": _valid_date(data.get("filed_date")),
            "events": events, "fault": fault}
