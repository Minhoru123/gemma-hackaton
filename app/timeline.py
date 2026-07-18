import sqlite3
import os
import config
from app import cases


def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    return sqlite3.connect(config.DB_PATH)


def _ensure_case_id(c) -> None:
    cols = [r[1] for r in c.execute("PRAGMA table_info(timeline)").fetchall()]
    if "case_id" not in cols:
        c.execute("ALTER TABLE timeline ADD COLUMN case_id INTEGER")


def init() -> None:
    c = _conn()
    c.execute(
        """CREATE TABLE IF NOT EXISTS timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT, label TEXT, when_ts TEXT
        )"""
    )
    _ensure_case_id(c)
    c.commit()
    c.close()


def add_event(kind: str, label: str, when: str) -> None:
    case_id = cases.active_id()
    c = _conn()
    c.execute(
        "INSERT INTO timeline (kind, label, when_ts, case_id) VALUES (?,?,?,?)",
        (kind, label, when, case_id),
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
    """Remove timeline events tied to one uploaded document in the active case.
    Events reference the document by filename in their label (e.g.
    'Filed: notice.txt (notice)', 'Uploaded notice.txt'). Returns rows removed."""
    case_id = cases.active_id()
    c = _conn()
    cur = c.execute(
        "DELETE FROM timeline WHERE case_id=? AND label LIKE ?",
        (case_id, f"%{source}%"),
    )
    c.commit()
    n = cur.rowcount
    c.close()
    return n
