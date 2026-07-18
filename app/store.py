import sqlite3
import json
import os
import numpy as np
import config
from app import ollama_client, cases


def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    return sqlite3.connect(config.DB_PATH)


def _ensure_case_id(c, table: str) -> None:
    """Add a case_id column to an existing table if it's missing (idempotent)."""
    cols = [r[1] for r in c.execute(f"PRAGMA table_info({table})").fetchall()]
    if "case_id" not in cols:
        c.execute(f"ALTER TABLE {table} ADD COLUMN case_id INTEGER")


def init_db() -> None:
    c = _conn()
    c.execute(
        """CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT, kind TEXT, text TEXT, embedding TEXT
        )"""
    )
    _ensure_case_id(c, "chunks")
    c.execute(
        "CREATE TABLE IF NOT EXISTS case_meta (key TEXT PRIMARY KEY, value TEXT)"
    )
    c.commit()
    c.close()


def get_meta(key: str) -> str:
    c = _conn()
    c.execute(
        "CREATE TABLE IF NOT EXISTS case_meta (key TEXT PRIMARY KEY, value TEXT)"
    )
    row = c.execute("SELECT value FROM case_meta WHERE key=?", (key,)).fetchone()
    c.close()
    return row[0] if row else ""


def set_meta(key: str, value: str) -> None:
    c = _conn()
    c.execute(
        "CREATE TABLE IF NOT EXISTS case_meta (key TEXT PRIMARY KEY, value TEXT)"
    )
    c.execute(
        "INSERT INTO case_meta (key, value) VALUES (?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    c.commit()
    c.close()


def add_chunks(source: str, chunks: list[str], kind: str) -> None:
    # Uploads are scoped to the active case; shared reference data (corpus,
    # authorities) is not tied to any case (case_id stays NULL).
    case_id = cases.active_id() if kind == "upload" else None
    c = _conn()
    for ch in chunks:
        emb = ollama_client.embed(ch)
        c.execute(
            "INSERT INTO chunks (source, kind, text, embedding, case_id) "
            "VALUES (?,?,?,?,?)",
            (source, kind, ch, json.dumps(emb), case_id),
        )
    c.commit()
    c.close()


def list_sources() -> list[dict]:
    """Uploaded documents in the ACTIVE case, with their captured chunk counts."""
    case_id = cases.active_id()
    c = _conn()
    rows = c.execute(
        "SELECT source, COUNT(*) FROM chunks "
        "WHERE kind='upload' AND case_id=? "
        "GROUP BY source ORDER BY MIN(id)",
        (case_id,),
    ).fetchall()
    c.close()
    return [{"source": s, "chunks": n} for s, n in rows]


def get_source_text(source: str) -> str:
    """Reconstruct one uploaded document's full text (active case) from its
    chunks, trimming the chunk overlap so text isn't duplicated at the seams."""
    case_id = cases.active_id()
    c = _conn()
    rows = c.execute(
        "SELECT text FROM chunks WHERE kind='upload' AND source=? AND case_id=? "
        "ORDER BY id",
        (source, case_id),
    ).fetchall()
    c.close()
    texts = [r[0] for r in rows]
    if not texts:
        return ""
    out = texts[0]
    for t in texts[1:]:
        if len(t) <= config.CHUNK_OVERLAP:
            continue  # wholly contained in the previous chunk's overlap
        out += t[config.CHUNK_OVERLAP:]
    return out


def remove_source(source: str) -> int:
    """Delete all upload chunks for one document in the active case. Returns the
    number of chunks removed. Corpus/authority chunks are never touched."""
    case_id = cases.active_id()
    c = _conn()
    cur = c.execute(
        "DELETE FROM chunks WHERE kind='upload' AND source=? AND case_id=?",
        (source, case_id),
    )
    c.commit()
    n = cur.rowcount
    c.close()
    return n


def remove_case(case_id: int) -> None:
    """Delete all upload chunks belonging to one case (used when the case itself
    is deleted). Takes an explicit case_id since the case may not be active.
    Shared reference chunks (case_id IS NULL) are never touched."""
    c = _conn()
    c.execute("DELETE FROM chunks WHERE kind='upload' AND case_id=?", (case_id,))
    c.commit()
    c.close()


def clear_uploads() -> None:
    """Remove all upload chunks for the active case (reference data untouched)."""
    case_id = cases.active_id()
    c = _conn()
    c.execute("DELETE FROM chunks WHERE kind='upload' AND case_id=?", (case_id,))
    c.commit()
    c.close()


def search(query: str, k: int = config.TOP_K) -> list[dict]:
    q = np.array(ollama_client.embed(query), dtype=np.float32)
    qn = q / (np.linalg.norm(q) + 1e-9)
    case_id = cases.active_id()
    c = _conn()
    # Shared reference data (case_id IS NULL) is always visible; uploads only
    # from the active case, so RAG never leaks one case's documents into another.
    rows = c.execute(
        "SELECT source, kind, text, embedding FROM chunks "
        "WHERE case_id IS NULL OR case_id=?",
        (case_id,),
    ).fetchall()
    c.close()
    scored = []
    for source, kind, text, emb_json in rows:
        v = np.array(json.loads(emb_json), dtype=np.float32)
        vn = v / (np.linalg.norm(v) + 1e-9)
        score = float(np.dot(qn, vn))
        scored.append({"text": text, "source": source, "kind": kind, "score": score})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:k]
