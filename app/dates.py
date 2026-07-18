"""Date parsing and validation for the timeline and deadline machinery.

Every date is handled as a full calendar date — month, day, AND year — and is
semantically validated (Feb 30 and month 13 are rejected, not just malformed
strings). All output is ISO YYYY-MM-DD so string comparison equals date
comparison everywhere else in the app."""

import re
import datetime

YEAR_MIN, YEAR_MAX = 1900, 2100

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_MONTH_PAT = (r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
              r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
              r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?")

# "April 14, 2026" / "Apr. 14 2026" / "April 14th, 2026"
_TEXTUAL_MDY = re.compile(
    rf"\b({_MONTH_PAT})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b",
    re.IGNORECASE)
# "14 April 2026" / "14th of April, 2026"
_TEXTUAL_DMY = re.compile(
    rf"\b(\d{{1,2}})(?:st|nd|rd|th)?(?:\s+of)?\s+({_MONTH_PAT})\.?,?\s+(\d{{4}})\b",
    re.IGNORECASE)
# "04/14/2026" / "4/14/26" (US month/day/year, incl. CM/ECF stamps)
_NUMERIC_MDY = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b")
# "2026-04-14"
_ISO = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")


def _expand_2digit_year(year: int) -> int:
    """26 -> 2026, 98 -> 1998. Only for slash forms like 4/14/26 — a literal
    four-digit year is never promoted."""
    return year + (2000 if year < 70 else 1900) if year < 100 else year


def _make(year: int, month: int, day: int) -> str:
    """ISO date if (year, month, day) is a real calendar date in a plausible
    year window, else ''."""
    try:
        d = datetime.date(year, month, day)
    except ValueError:
        return ""
    return d.isoformat() if YEAR_MIN <= d.year <= YEAR_MAX else ""


def _month_num(name: str) -> int:
    return _MONTHS.get(name.lower()[:3], 0)


def find_date(*texts: str) -> str:
    """The first full date found in any text, in document order, as ISO —
    or '' if none. Understands textual, numeric (US m/d/y), and ISO forms;
    candidates that aren't real calendar dates are skipped."""
    for text in texts:
        text = text or ""
        candidates = []  # (position, iso)
        for m in _TEXTUAL_MDY.finditer(text):
            iso = _make(int(m.group(3)), _month_num(m.group(1)), int(m.group(2)))
            if iso:
                candidates.append((m.start(), iso))
        for m in _TEXTUAL_DMY.finditer(text):
            iso = _make(int(m.group(3)), _month_num(m.group(2)), int(m.group(1)))
            if iso:
                candidates.append((m.start(), iso))
        for m in _NUMERIC_MDY.finditer(text):
            iso = _make(_expand_2digit_year(int(m.group(3))),
                        int(m.group(1)), int(m.group(2)))
            if iso:
                candidates.append((m.start(), iso))
        for m in _ISO.finditer(text):
            iso = _make(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if iso:
                candidates.append((m.start(), iso))
        if candidates:
            return min(candidates)[1]
    return ""


def valid_iso(s) -> str:
    """s if it is a semantically valid ISO date (real month/day, plausible
    year), normalized to YYYY-MM-DD — else ''."""
    s = str(s or "").strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    if not m:
        return ""
    return _make(int(m.group(1)), int(m.group(2)), int(m.group(3)))
