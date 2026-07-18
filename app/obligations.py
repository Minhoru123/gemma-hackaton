"""Open-obligations tracker (THREADS-lite): a filing or order created a duty,
with a due date that is either human-confirmed or presumptive, owed by one
side of the caption. Warnings are computed from what is still open — shown
when the app is opened, never pushed — and can be filtered to one side's view."""

from __future__ import annotations
import sqlite3
import os
import datetime
import config
from app import cases

DUE_SOON_DAYS = 7


def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    return sqlite3.connect(config.DB_PATH)


def _ensure_case_id(c) -> None:
    cols = [r[1] for r in c.execute("PRAGMA table_info(obligations)").fetchall()]
    if "case_id" not in cols:
        c.execute("ALTER TABLE obligations ADD COLUMN case_id INTEGER")
    if "owed_by" not in cols:
        # Whose duty this is: 'plaintiff' | 'defendant' | '' (unknown — shown
        # in every view). Legacy rows migrate as ''.
        c.execute("ALTER TABLE obligations ADD COLUMN owed_by TEXT DEFAULT ''")


def init() -> None:
    c = _conn()
    c.execute(
        """CREATE TABLE IF NOT EXISTS obligations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT, trigger_source TEXT, due_date TEXT,
            presumptive INTEGER DEFAULT 1, rule_cite TEXT,
            satisfied_by TEXT, status TEXT DEFAULT 'open', created TEXT
        )"""
    )
    _ensure_case_id(c)
    c.commit()
    c.close()


def add(label: str, trigger_source: str = "", due_date: str = "",
        presumptive: bool = True, rule_cite: str = "",
        satisfied_by: str = "", owed_by: str = "") -> int:
    case_id = cases.active_id()
    c = _conn()
    cur = c.execute(
        """INSERT INTO obligations
           (label, trigger_source, due_date, presumptive, rule_cite,
            satisfied_by, created, case_id, owed_by)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (label, trigger_source, due_date, int(presumptive), rule_cite,
         satisfied_by, datetime.date.today().isoformat(), case_id, owed_by),
    )
    c.commit()
    oid = cur.lastrowid
    c.close()
    return oid


_KEYS = ["id", "label", "trigger_source", "due_date", "presumptive",
         "rule_cite", "satisfied_by", "created", "owed_by"]
_COLS = ", ".join(_KEYS)


def list_open() -> list[dict]:
    case_id = cases.active_id()
    c = _conn()
    rows = c.execute(
        f"""SELECT {_COLS} FROM obligations
            WHERE status='open' AND case_id=? ORDER BY due_date""",
        (case_id,),
    ).fetchall()
    c.close()
    return [dict(zip(_KEYS, r)) for r in rows]


def get(oid: int) -> dict | None:
    case_id = cases.active_id()
    c = _conn()
    row = c.execute(
        f"SELECT {_COLS} FROM obligations WHERE id=? AND case_id=?",
        (oid, case_id),
    ).fetchone()
    c.close()
    return dict(zip(_KEYS, row)) if row else None


def list_all() -> list[dict]:
    """Every obligation of the active case, open or satisfied — the durable
    record of computed deadlines (used to rebuild the timeline)."""
    case_id = cases.active_id()
    c = _conn()
    rows = c.execute(
        f"""SELECT {_COLS}, status FROM obligations
            WHERE case_id=? ORDER BY due_date""",
        (case_id,),
    ).fetchall()
    c.close()
    return [dict(zip(_KEYS + ["status"], r)) for r in rows]


def satisfy(oid: int) -> None:
    c = _conn()
    c.execute("UPDATE obligations SET status='satisfied' WHERE id=?", (oid,))
    c.commit()
    c.close()


def remove_case(case_id: int) -> None:
    """Delete every obligation of one case (used when the case is deleted). Takes
    an explicit case_id since the case may not be active."""
    c = _conn()
    c.execute("DELETE FROM obligations WHERE case_id=?", (case_id,))
    c.commit()
    c.close()


def try_satisfy(doc_type: str, filed_by: str = "") -> list[str]:
    """When a document of this type is uploaded, mark open obligations in the
    active case waiting on that type as satisfied. When the filer's side is
    known, only that side's obligations are satisfied — the defendant's
    opposition doesn't discharge the plaintiff's. Unknown filer (or an
    obligation with unknown owner) matches either way. Returns labels satisfied."""
    if not doc_type:
        return []
    case_id = cases.active_id()
    c = _conn()
    rows = c.execute(
        "SELECT id, label, owed_by FROM obligations "
        "WHERE status='open' AND satisfied_by=? AND case_id=?",
        (doc_type, case_id),
    ).fetchall()
    satisfied = []
    for oid, label, owed_by in rows:
        if filed_by and owed_by and filed_by != owed_by:
            continue
        c.execute("UPDATE obligations SET status='satisfied' WHERE id=?", (oid,))
        satisfied.append(label)
    c.commit()
    c.close()
    return satisfied


def warnings(today: str = "", view: str = "") -> list[dict]:
    """Open obligations with urgency: overdue, due_soon (within DUE_SOON_DAYS),
    or open (no date / not yet close). With view ('plaintiff'/'defendant'),
    only that side's duties (plus unknown-owner ones) are returned."""
    today = today or datetime.date.today().isoformat()
    out = []
    for ob in list_open():
        if view and ob["owed_by"] and ob["owed_by"] != view:
            continue
        if ob["due_date"] and ob["due_date"] < today:
            urgency = "overdue"
        elif ob["due_date"]:
            due = datetime.date.fromisoformat(ob["due_date"])
            delta = (due - datetime.date.fromisoformat(today)).days
            urgency = "due_soon" if delta <= DUE_SOON_DAYS else "open"
        else:
            urgency = "open"
        out.append({**ob, "urgency": urgency})
    order = {"overdue": 0, "due_soon": 1, "open": 2}
    out.sort(key=lambda w: (order[w["urgency"]], w["due_date"] or "9999"))
    return out
