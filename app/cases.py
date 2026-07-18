"""Active-case state for per-case documentation isolation.

Owns the `cases` table and which single case is active. Every case-specific
store (chunks, timeline, questions, obligations) reads `active_id()` internally
to scope its rows. Single-user on-device app: exactly one active case at a time.

Depends only on the DB (no import cycle with the other stores)."""

import sqlite3
import os
import datetime
import config


def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    return sqlite3.connect(config.DB_PATH)


def init() -> None:
    """Create the cases table; if empty, create 'My case' and make it active so
    the app is never in a no-active-case state."""
    c = _conn()
    c.execute(
        """CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, created TEXT, is_active INTEGER DEFAULT 0
        )"""
    )
    c.commit()
    n = c.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    c.close()
    if n == 0:
        create("My case")


def list_all() -> list[dict]:
    c = _conn()
    rows = c.execute(
        "SELECT id, name, created, is_active FROM cases ORDER BY id DESC"
    ).fetchall()
    c.close()
    return [{"id": i, "name": nm, "created": cr, "is_active": bool(a)}
            for (i, nm, cr, a) in rows]


def active_id() -> int:
    """The active case id. Always returns a valid id: self-heals by activating
    the most recent case, or creating 'My case' if the table is empty."""
    c = _conn()
    c.execute(
        """CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, created TEXT, is_active INTEGER DEFAULT 0
        )"""
    )
    row = c.execute("SELECT id FROM cases WHERE is_active=1 LIMIT 1").fetchone()
    if row:
        c.close()
        return row[0]
    # No active case: activate the most recent, or create one.
    recent = c.execute("SELECT id FROM cases ORDER BY id DESC LIMIT 1").fetchone()
    c.close()
    if recent:
        set_active(recent[0])
        return recent[0]
    return create("My case")


def create(name: str) -> int:
    """Insert a new case, switch to it, and return its id. Blank name falls back
    to 'Untitled case'."""
    name = (name or "").strip() or "Untitled case"
    c = _conn()
    cur = c.execute(
        "INSERT INTO cases (name, created, is_active) VALUES (?,?,0)",
        (name, datetime.date.today().isoformat()),
    )
    new_id = cur.lastrowid
    c.commit()
    c.close()
    set_active(new_id)
    return new_id


def rename(case_id: int, name: str) -> None:
    """Rename a case. Blank name is ignored (keeps the current name). Renaming a
    non-existent id is a no-op."""
    name = (name or "").strip()
    if not name:
        return
    c = _conn()
    c.execute("UPDATE cases SET name=? WHERE id=?", (name, case_id))
    c.commit()
    c.close()


def delete(case_id: int) -> bool:
    """Delete a case's row. No-op returning False if it's the last case (the app
    must always have one) or the id doesn't exist. If the deleted case was
    active, activate the most recent remaining case so we're never left without
    an active case. Returns True if a case was removed.

    This deletes only the `cases` row; the per-case stores own the deletion of
    their own scoped rows (no import cycle)."""
    c = _conn()
    n = c.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    if n <= 1:
        c.close()
        return False
    row = c.execute("SELECT is_active FROM cases WHERE id=?", (case_id,)).fetchone()
    if row is None:
        c.close()
        return False
    was_active = bool(row[0])
    c.execute("DELETE FROM cases WHERE id=?", (case_id,))
    c.commit()
    c.close()
    if was_active:
        recent = _conn()
        r = recent.execute("SELECT id FROM cases ORDER BY id DESC LIMIT 1").fetchone()
        recent.close()
        if r:
            set_active(r[0])
    return True


def set_active(case_id: int) -> None:
    """Make exactly one case active. Switching to a non-existent id is a no-op
    (leaves current state unchanged) rather than clearing all active flags."""
    c = _conn()
    exists = c.execute("SELECT 1 FROM cases WHERE id=?", (case_id,)).fetchone()
    if not exists:
        c.close()
        return
    c.execute("UPDATE cases SET is_active=0")
    c.execute("UPDATE cases SET is_active=1 WHERE id=?", (case_id,))
    c.commit()
    c.close()
