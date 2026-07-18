"""Which court system governs this case: Utah state or federal.

A case is governed by ONE rule set — Utah state rules or federal rules, never
both. The court is read from the filings themselves, caption first: the court
name at the top of a filing is authoritative, because body text misleads (a
federal brief may cite Utah statutes and name the State of Utah as a party;
a state brief may discuss federal cases). Whole-document signals (rule cites,
federal case-number formats) are used only when the caption says nothing, and
only when they point one way.

The first document that reveals the court fixes the case's jurisdiction; it is
persisted in case_meta. Later documents that appear to come from the OTHER
court system are surfaced as an ask-your-attorney question, not silently
switched — a wrong-court filing is exactly the kind of thing a human must see.
"""

import re
from app import store

UTAH = "utah"
FEDERAL = "federal"

LABELS = {UTAH: "Utah state court", FEDERAL: "federal court"}

# How much of the document counts as the caption region. Court captions sit at
# the top of page 1; 2000 chars comfortably covers caption + title.
_CAPTION_CHARS = 2000

_FEDERAL_CAPTION = re.compile(
    r"\bUNITED STATES DISTRICT COURT\b"
    r"|\bU\.?\s?S\.? DISTRICT COURT\b"
    r"|\bUNITED STATES (?:BANKRUPTCY|MAGISTRATE) (?:COURT|JUDGE)\b"
    r"|\bUNITED STATES COURT OF APPEALS\b"
    r"|\bIN THE DISTRICT COURT OF THE UNITED STATES\b"
    r"|\bFOR THE DISTRICT OF UTAH\b",
    re.IGNORECASE)

_UTAH_CAPTION = re.compile(
    r"\b(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH)\s+"
    r"(?:JUDICIAL\s+)?DISTRICT\s+(?:COURT|JUVENILE COURT)\b"
    r"|\bJUDICIAL DISTRICT COURT\b"
    r"|\bDISTRICT COURT[^\n]{0,80}STATE OF UTAH\b"
    r"|\bSTATE OF UTAH[^\n]{0,80}DISTRICT COURT\b"
    r"|\bUTAH COURT OF APPEALS\b"
    r"|\b(?:UTAH SUPREME COURT|SUPREME COURT OF (?:THE STATE OF )?UTAH)\b"
    r"|\bJUSTICE COURT\b"
    r"|\bIN THE (?:DISTRICT|JUVENILE) COURT OF [^\n]{0,60}\bUTAH\b",
    re.IGNORECASE)

# Weak signals, whole document. Used only when the caption is silent, and only
# when they do not contradict each other.
_FEDERAL_WEAK = re.compile(
    r"\bFed\.?\s?R\.?\s?Civ\.?\s?P\b"
    r"|\bFederal Rules? of Civil Procedure\b"
    r"|\bDUCivR\b"
    r"|\b\d:\d{2}-(?:cv|cr|mc|md|bk)-\d{2,}\b",
    re.IGNORECASE)

_UTAH_WEAK = re.compile(
    r"\bUtah R\.?\s?Civ\.?\s?P\b"
    r"|\bUtah Rules? of Civil Procedure\b"
    r"|\bURCP\b"
    r"|\bUtah R\.?\s?Crim\.?\s?P\b",
    re.IGNORECASE)


def detect(text: str) -> str:
    """Return 'utah', 'federal', or '' when the document doesn't say."""
    head = text[:_CAPTION_CHARS]
    fed_cap = bool(_FEDERAL_CAPTION.search(head))
    utah_cap = bool(_UTAH_CAPTION.search(head))
    if fed_cap != utah_cap:
        return FEDERAL if fed_cap else UTAH
    if fed_cap and utah_cap:
        return ""  # contradictory caption region — let a human decide
    fed = bool(_FEDERAL_WEAK.search(text))
    utah = bool(_UTAH_WEAK.search(text))
    if fed != utah:
        return FEDERAL if fed else UTAH
    return ""


def get_case() -> str:
    """The persisted jurisdiction of the ACTIVE case ('' until a filing
    reveals it). Scoped per case — two cases can be in different courts."""
    from app import cases
    return store.get_meta(f"jurisdiction:{cases.active_id()}")


def set_case(jurisdiction: str) -> None:
    from app import cases
    if jurisdiction in (UTAH, FEDERAL):
        store.set_meta(f"jurisdiction:{cases.active_id()}", jurisdiction)


def migrate_legacy() -> None:
    """Early versions stored one global 'jurisdiction' key. Attribute it to the
    active case (the only case that could have set it) and retire the key."""
    legacy = store.get_meta("jurisdiction")
    if legacy and not get_case():
        set_case(legacy)
    if legacy:
        store.set_meta("jurisdiction", "")
