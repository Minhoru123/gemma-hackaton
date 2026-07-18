"""Ask-your-attorney list: things the system noticed that a human should raise
with counsel. The system never contacts the lawyer — it only surfaces
questions to the user."""

import sqlite3
import os
import datetime
import config


def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    return sqlite3.connect(config.DB_PATH)


def init() -> None:
    c = _conn()
    c.execute(
        """CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT UNIQUE, source TEXT, context_quote TEXT,
            created TEXT, status TEXT DEFAULT 'open'
        )"""
    )
    c.commit()
    c.close()


def add(question: str, source: str = "", context_quote: str = "") -> bool:
    """Add a question; duplicates are ignored. Returns True if newly added."""
    c = _conn()
    cur = c.execute(
        """INSERT OR IGNORE INTO questions (question, source, context_quote, created)
           VALUES (?,?,?,?)""",
        (question.strip(), source, context_quote,
         datetime.date.today().isoformat()),
    )
    c.commit()
    added = cur.rowcount > 0
    c.close()
    return added


def list_open() -> list[dict]:
    c = _conn()
    rows = c.execute(
        """SELECT id, question, source, context_quote, created
           FROM questions WHERE status='open' ORDER BY id DESC"""
    ).fetchall()
    c.close()
    keys = ["id", "question", "source", "context_quote", "created"]
    return [dict(zip(keys, r)) for r in rows]


def resolve(qid: int) -> None:
    c = _conn()
    c.execute("UPDATE questions SET status='resolved' WHERE id=?", (qid,))
    c.commit()
    c.close()
