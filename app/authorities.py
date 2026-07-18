"""Authorities library: every citation a draft may use must be a row here,
with captured full text and provenance. Nothing uncaptured goes in a draft."""

from __future__ import annotations
import re
import sqlite3
import os
import config


def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    return sqlite3.connect(config.DB_PATH)


def init_db() -> None:
    c = _conn()
    c.execute(
        """CREATE TABLE IF NOT EXISTS authorities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, citation TEXT, canonical TEXT UNIQUE,
            type TEXT, court TEXT, year TEXT,
            holding TEXT, captured_text TEXT,
            source_url TEXT, retrieved_date TEXT, confirmed_by TEXT
        )"""
    )
    c.commit()
    c.close()


def canonicalize(cite: str) -> str:
    """Normalize a citation to a stable comparison key."""
    s = cite.replace("–", "-").replace("—", "-")
    s = s.replace("§§", "§")
    s = re.sub(r"§\s*", "§ ", s)
    s = " ".join(s.split())
    s = s.strip(" ,;.")
    return s.upper()


def add_authority(name: str, citation: str, captured_text: str, type: str = "case",
                  court: str = "", year: str = "", holding: str = "",
                  source_url: str = "", retrieved_date: str = "",
                  confirmed_by: str = "") -> None:
    c = _conn()
    c.execute(
        """INSERT OR REPLACE INTO authorities
           (name, citation, canonical, type, court, year, holding,
            captured_text, source_url, retrieved_date, confirmed_by)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (name, citation, canonicalize(citation), type, court, year, holding,
         captured_text, source_url, retrieved_date, confirmed_by),
    )
    c.commit()
    c.close()


def get_by_citation(cite: str) -> dict | None:
    c = _conn()
    row = c.execute(
        """SELECT name, citation, type, court, year, holding, captured_text,
                  source_url, retrieved_date, confirmed_by
           FROM authorities WHERE canonical = ?""",
        (canonicalize(cite),),
    ).fetchone()
    c.close()
    if not row:
        return None
    keys = ["name", "citation", "type", "court", "year", "holding",
            "captured_text", "source_url", "retrieved_date", "confirmed_by"]
    return dict(zip(keys, row))


def list_authorities() -> list[dict]:
    c = _conn()
    rows = c.execute(
        "SELECT name, citation, type, confirmed_by FROM authorities ORDER BY name"
    ).fetchall()
    c.close()
    return [{"name": n, "citation": ci, "type": t, "confirmed_by": cb}
            for (n, ci, t, cb) in rows]


# Citation patterns: neutral cites, common reporters, statutes, court rules.
_PATTERNS = [
    r"\b\d{4}\s+UT(?:\s+App)?\s+\d+\b",                       # 2020 UT 51
    r"\b\d+\s+U\.S\.\s+\d+\b",                                # 550 U.S. 544
    r"\b\d+\s+S\.\s?Ct\.\s+\d+\b",                            # 141 S. Ct. 792
    r"\b\d+\s+F\.\s?(?:2d|3d|4th)\s+\d+\b",                   # 123 F.3d 456
    r"\b\d+\s+F\.\s?Supp\.(?:\s?(?:2d|3d))?\s+\d+\b",         # 87 F. Supp. 2d 1
    r"\b\d+\s+P\.\s?(?:2d|3d)\s+\d+\b",                       # 472 P.3d 843
    r"\b\d+\s+U\.S\.C\.\s*§{1,2}\s*\d+[a-zA-Z0-9().\-]*",  # 42 U.S.C. § 1983
    r"\bUtah\s+Code(?:\s+Ann\.)?\s*§{1,2}\s*[0-9][0-9a-zA-Z.\-]*",
    r"\b(?:URCP|URAP|DUCivR)\s+\d+[a-zA-Z0-9().]*",           # URCP 7(q)
    r"\bFed\.\s?R\.\s?(?:Civ|App|Evid)\.\s?P\.\s+\d+[a-zA-Z0-9().]*",
]
_CITE_RE = re.compile("|".join(f"(?:{p})" for p in _PATTERNS))


def extract_citations(text: str) -> list[str]:
    """Unique citations found in text, in order of first appearance."""
    seen, out = set(), []
    for m in _CITE_RE.finditer(text):
        key = canonicalize(m.group(0))
        if key not in seen:
            seen.add(key)
            out.append(m.group(0).strip(" ,;."))
    return out


def diff_citations(text: str) -> dict:
    """Split a document's citations into library-known (confirmed),
    unconfirmed (captured but awaiting sign-off), and unknown."""
    known, unconfirmed, unknown = [], [], []
    for cite in extract_citations(text):
        row = get_by_citation(cite)
        if row is None:
            unknown.append(cite)
        elif not row["confirmed_by"]:
            unconfirmed.append(cite)
        else:
            known.append(cite)
    return {"known": known, "unconfirmed": unconfirmed, "unknown": unknown}
