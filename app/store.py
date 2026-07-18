import sqlite3
import json
import os
import numpy as np
import config
from app import ollama_client


def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    return sqlite3.connect(config.DB_PATH)


def init_db() -> None:
    c = _conn()
    c.execute(
        """CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT, kind TEXT, text TEXT, embedding TEXT
        )"""
    )
    c.commit()
    c.close()


def add_chunks(source: str, chunks: list[str], kind: str) -> None:
    c = _conn()
    for ch in chunks:
        emb = ollama_client.embed(ch)
        c.execute(
            "INSERT INTO chunks (source, kind, text, embedding) VALUES (?,?,?,?)",
            (source, kind, ch, json.dumps(emb)),
        )
    c.commit()
    c.close()


def clear_uploads() -> None:
    c = _conn()
    c.execute("DELETE FROM chunks WHERE kind='upload'")
    c.commit()
    c.close()


def search(query: str, k: int = config.TOP_K) -> list[dict]:
    q = np.array(ollama_client.embed(query), dtype=np.float32)
    qn = q / (np.linalg.norm(q) + 1e-9)
    c = _conn()
    rows = c.execute("SELECT source, kind, text, embedding FROM chunks").fetchall()
    c.close()
    scored = []
    for source, kind, text, emb_json in rows:
        v = np.array(json.loads(emb_json), dtype=np.float32)
        vn = v / (np.linalg.norm(v) + 1e-9)
        score = float(np.dot(qn, vn))
        scored.append({"text": text, "source": source, "kind": kind, "score": score})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:k]
