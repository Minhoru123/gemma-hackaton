"""Mechanical draft verification: every citation must resolve to a confirmed
authorities-library row, every quotation must match captured text verbatim
(elision- and bracket-tolerant), and no [[MARKER]] may remain. Unresolved
anything = failure."""

import re
import config
from app import authorities, coverage

_MARKER_RE = re.compile(r"\[\[[^\]]+\]\]")
_QUOTE_RE = re.compile(r"[“\"]([^“”\"]+)[”\"]")
_ELLIPSIS_RE = re.compile(r"…|\.\s?\.\s?\.")


def find_markers(text: str) -> list[str]:
    return _MARKER_RE.findall(text)


def extract_quotes(text: str) -> list[str]:
    """Quoted passages long enough to be treated as verbatim quotations."""
    return [q.strip() for q in _QUOTE_RE.findall(text)
            if len(q.strip()) >= config.MIN_QUOTE_CHARS]


def _norm(s: str) -> str:
    """Normalize for verbatim comparison: unify quote/dash glyphs, unwrap
    [bracketed] alterations, collapse whitespace, lowercase."""
    s = (s.replace("“", '"').replace("”", '"')
          .replace("‘", "'").replace("’", "'")
          .replace("–", "-").replace("—", "-"))
    s = re.sub(r"\[([^\]]*)\]", r"\1", s)
    s = " ".join(s.split())
    return s.lower()


def quote_matches(quote: str, captured: str) -> bool:
    """True if every ellipsis-separated segment of the quote appears in the
    captured text, in order."""
    hay = _norm(captured)
    pos = 0
    for seg in _ELLIPSIS_RE.split(quote):
        seg = _norm(seg).strip(" .,;:")
        if not seg:
            continue
        i = hay.find(seg, pos)
        if i < 0:
            return False
        pos = i + len(seg)
    return True


def verify_draft(text: str, coverage_text: str = "") -> dict:
    """Run all mechanical checks on a draft. Returns a report; report["ok"]
    is False on any hard failure."""
    cites = authorities.diff_citations(text)

    captures = [r["captured_text"]
                for c in cites["known"]
                for r in authorities.get_all_by_citation(c)
                if r["captured_text"]]
    matched, unmatched = [], []
    for q in extract_quotes(text):
        (matched if any(quote_matches(q, cap) for cap in captures)
         else unmatched).append(q)

    markers = find_markers(text)
    unanswered = coverage.unanswered(coverage_text) if coverage_text else []

    failures = (cites["unknown"] or cites["unconfirmed"] or unmatched
                or markers or unanswered)
    return {
        "citations": cites,
        "quotes": {"matched": matched, "unmatched": unmatched},
        "markers": markers,
        "coverage_unanswered": unanswered,
        "ok": not failures,
    }


def format_report(report: dict) -> str:
    lines = []
    c = report["citations"]
    lines.append(f"Citations: {len(c['known'])} resolved, "
                 f"{len(c['unconfirmed'])} unconfirmed, {len(c['unknown'])} unknown")
    for cite in c["unknown"]:
        lines.append(f"  FAIL not in library: {cite}")
    for cite in c["unconfirmed"]:
        lines.append(f"  FAIL captured but unconfirmed: {cite}")
    q = report["quotes"]
    lines.append(f"Quotes: {len(q['matched'])} matched, {len(q['unmatched'])} unmatched")
    for quote in q["unmatched"]:
        lines.append(f'  FAIL no verbatim match: "{quote[:70]}"')
    for m in report["markers"]:
        lines.append(f"  FAIL unresolved marker: {m}")
    for item in report["coverage_unanswered"]:
        lines.append(f"  FAIL contention unanswered: {item}")
    lines.append("VERIFY: " + ("CLEAN" if report["ok"] else "FAILED"))
    return "\n".join(lines)
