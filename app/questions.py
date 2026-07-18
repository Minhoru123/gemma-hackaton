"""Ask-your-attorney list: things the system noticed that a human should raise
with counsel. The system never contacts the lawyer — it only surfaces
questions to the user."""

import sqlite3
import os
import datetime
import config
from app import cases


def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    return sqlite3.connect(config.DB_PATH)


def _ensure_case_id(c) -> None:
    cols = [r[1] for r in c.execute("PRAGMA table_info(questions)").fetchall()]
    if "case_id" not in cols:
        c.execute("ALTER TABLE questions ADD COLUMN case_id INTEGER")


def init() -> None:
    c = _conn()
    # NOTE: the legacy table has a column-level UNIQUE on `question`. We keep it
    # but enforce per-case uniqueness manually in add(), so the same question can
    # exist in two different cases.
    c.execute(
        """CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT, source TEXT, context_quote TEXT,
            created TEXT, status TEXT DEFAULT 'open'
        )"""
    )
    _ensure_case_id(c)
    c.commit()
    c.close()


def add(question: str, source: str = "", context_quote: str = "") -> bool:
    """Add a question to the active case; duplicates within the same case are
    ignored. Returns True if newly added."""
    question = question.strip()
    case_id = cases.active_id()
    c = _conn()
    exists = c.execute(
        "SELECT 1 FROM questions WHERE case_id=? AND question=?",
        (case_id, question),
    ).fetchone()
    if exists:
        c.close()
        return False
    c.execute(
        """INSERT INTO questions (question, source, context_quote, created, case_id)
           VALUES (?,?,?,?,?)""",
        (question, source, context_quote,
         datetime.date.today().isoformat(), case_id),
    )
    c.commit()
    c.close()
    return True


def list_open() -> list[dict]:
    case_id = cases.active_id()
    c = _conn()
    rows = c.execute(
        """SELECT id, question, source, context_quote, created
           FROM questions WHERE status='open' AND case_id=? ORDER BY id DESC""",
        (case_id,),
    ).fetchall()
    c.close()
    keys = ["id", "question", "source", "context_quote", "created"]
    return [dict(zip(keys, r)) for r in rows]


def resolve(qid: int) -> None:
    c = _conn()
    c.execute("UPDATE questions SET status='resolved' WHERE id=?", (qid,))
    c.commit()
    c.close()


def remove_by_source(source: str) -> int:
    """Remove questions the system generated from one uploaded document in the
    active case. User-added questions (source='user') are kept."""
    case_id = cases.active_id()
    c = _conn()
    cur = c.execute(
        "DELETE FROM questions WHERE case_id=? AND source=?",
        (case_id, source),
    )
    c.commit()
    n = cur.rowcount
    c.close()
    return n
