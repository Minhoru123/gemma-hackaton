"""Which side of the caption the user is on: plaintiff/petitioner or
defendant/respondent. Set at case setup by the user — never inferred silently,
because getting it wrong flips whose deadlines are whose. Stored per case."""

from app import store, cases

PLAINTIFF = "plaintiff"   # includes petitioner
DEFENDANT = "defendant"   # includes respondent

LABELS = {PLAINTIFF: "Plaintiff / Petitioner", DEFENDANT: "Defendant / Respondent"}

_PLAINTIFF_WORDS = ("plaintiff", "petitioner")
_DEFENDANT_WORDS = ("defendant", "respondent")


def get() -> str:
    """'plaintiff', 'defendant', or '' if the user hasn't said yet."""
    return store.get_meta(f"role:{cases.active_id()}")


def set(role: str) -> None:
    if role in (PLAINTIFF, DEFENDANT):
        store.set_meta(f"role:{cases.active_id()}", role)


def side_of(text: str) -> str:
    """Which caption side a phrase refers to ('plaintiff'/'defendant'/'').
    'Petitioner's counsel' -> plaintiff side; 'Respondent' -> defendant side."""
    low = (text or "").lower()
    p = any(w in low for w in _PLAINTIFF_WORDS)
    d = any(w in low for w in _DEFENDANT_WORDS)
    if p == d:  # neither, or both mentioned — can't tell
        return ""
    return PLAINTIFF if p else DEFENDANT


def origin(filed_by: str) -> str:
    """Who a document came from, relative to the user: 'user', 'opponent', or
    '' when the role or the filer is unknown (or the court issued it)."""
    role = get()
    if not role or filed_by not in (PLAINTIFF, DEFENDANT):
        return ""
    return "user" if filed_by == role else "opponent"
