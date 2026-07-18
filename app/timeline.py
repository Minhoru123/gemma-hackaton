import sqlite3
import os
import config
from app import cases


def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    return sqlite3.connect(config.DB_PATH)


def _ensure_columns(c) -> None:
    cols = [r[1] for r in c.execute("PRAGMA table_info(timeline)").fetchall()]
    if "case_id" not in cols:
        c.execute("ALTER TABLE timeline ADD COLUMN case_id INTEGER")
    if "source" not in cols:
        c.execute("ALTER TABLE timeline ADD COLUMN source TEXT")


def init() -> None:
    c = _conn()
    c.execute(
        """CREATE TABLE IF NOT EXISTS timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT, label TEXT, when_ts TEXT
        )"""
    )
    _ensure_columns(c)
    c.commit()
    c.close()


def add_event(kind: str, label: str, when: str, source: str = "") -> None:
    """Record a timeline event. `source` is the uploaded document it came from
    (if any), so removing that document can remove its events precisely."""
    case_id = cases.active_id()
    c = _conn()
    c.execute(
        "INSERT INTO timeline (kind, label, when_ts, case_id, source) "
        "VALUES (?,?,?,?,?)",
        (kind, label, when, case_id, source),
    )
    c.commit()
    c.close()


def list_events() -> list[dict]:
    case_id = cases.active_id()
    c = _conn()
    rows = c.execute(
        "SELECT kind, label, when_ts FROM timeline WHERE case_id=? ORDER BY when_ts",
        (case_id,),
    ).fetchall()
    c.close()
    return [{"kind": k, "label": l, "when": w} for (k, l, w) in rows]


def remove_by_source(source: str) -> int:
    """Remove all timeline events tied to one uploaded document in the active
    case. Matches on the recorded `source` column, falling back to a label match
    for any legacy rows written before the column existed. Returns rows removed."""
    case_id = cases.active_id()
    c = _conn()
    cur = c.execute(
        "DELETE FROM timeline WHERE case_id=? AND (source=? OR label LIKE ?)",
        (case_id, source, f"%{source}%"),
    )
    c.commit()
    n = cur.rowcount
    c.close()
    return n
