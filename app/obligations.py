"""Open-obligations tracker (THREADS-lite): a filing or order created a duty,
with a due date that is either human-confirmed or presumptive. Warnings are
computed from what is still open — shown when the app is opened, never pushed."""

import sqlite3
import os
import datetime
import config

DUE_SOON_DAYS = 7


def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    return sqlite3.connect(config.DB_PATH)


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
    c.commit()
    c.close()


def add(label: str, trigger_source: str = "", due_date: str = "",
        presumptive: bool = True, rule_cite: str = "",
        satisfied_by: str = "") -> int:
    c = _conn()
    cur = c.execute(
        """INSERT INTO obligations
           (label, trigger_source, due_date, presumptive, rule_cite,
            satisfied_by, created)
           VALUES (?,?,?,?,?,?,?)""",
        (label, trigger_source, due_date, int(presumptive), rule_cite,
         satisfied_by, datetime.date.today().isoformat()),
    )
    c.commit()
    oid = cur.lastrowid
    c.close()
    return oid


def list_open() -> list[dict]:
    c = _conn()
    rows = c.execute(
        """SELECT id, label, trigger_source, due_date, presumptive, rule_cite,
                  satisfied_by, created
           FROM obligations WHERE status='open' ORDER BY due_date"""
    ).fetchall()
    c.close()
    keys = ["id", "label", "trigger_source", "due_date", "presumptive",
            "rule_cite", "satisfied_by", "created"]
    return [dict(zip(keys, r)) for r in rows]


def satisfy(oid: int) -> None:
    c = _conn()
    c.execute("UPDATE obligations SET status='satisfied' WHERE id=?", (oid,))
    c.commit()
    c.close()


def try_satisfy(doc_type: str) -> list[str]:
    """When a document of this type is uploaded, mark open obligations waiting
    on that type as satisfied. Returns the labels satisfied."""
    if not doc_type:
        return []
    c = _conn()
    rows = c.execute(
        "SELECT id, label FROM obligations WHERE status='open' AND satisfied_by=?",
        (doc_type,),
    ).fetchall()
    for oid, _ in rows:
        c.execute("UPDATE obligations SET status='satisfied' WHERE id=?", (oid,))
    c.commit()
    c.close()
    return [label for _, label in rows]


def warnings(today: str = "") -> list[dict]:
    """Open obligations with urgency: overdue, due_soon (within DUE_SOON_DAYS),
    or open (no date / not yet close)."""
    today = today or datetime.date.today().isoformat()
    out = []
    for ob in list_open():
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
