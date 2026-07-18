import sqlite3
import os
import config


def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    return sqlite3.connect(config.DB_PATH)


def init() -> None:
    c = _conn()
    c.execute(
        """CREATE TABLE IF NOT EXISTS timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT, label TEXT, when_ts TEXT
        )"""
    )
    c.commit()
    c.close()


def add_event(kind: str, label: str, when: str) -> None:
    c = _conn()
    c.execute("INSERT INTO timeline (kind, label, when_ts) VALUES (?,?,?)",
              (kind, label, when))
    c.commit()
    c.close()


def list_events() -> list[dict]:
    c = _conn()
    rows = c.execute(
        "SELECT kind, label, when_ts FROM timeline ORDER BY when_ts"
    ).fetchall()
    c.close()
    return [{"kind": k, "label": l, "when": w} for (k, l, w) in rows]
