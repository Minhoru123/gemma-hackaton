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


_CREATE_AUTHORITIES = """CREATE TABLE IF NOT EXISTS authorities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT, citation TEXT, canonical TEXT,
    type TEXT, court TEXT, year TEXT,
    holding TEXT, captured_text TEXT,
    source_url TEXT, retrieved_date TEXT, confirmed_by TEXT
)"""


def init_db() -> None:
    c = _conn()
    # A citation may legitimately have several captures (statute versions,
    # history packets, parallel documents), so canonical is NOT unique.
    # Migrate any legacy table that still carries the UNIQUE constraint.
    row = c.execute("SELECT sql FROM sqlite_master WHERE type='table' "
                    "AND name='authorities'").fetchone()
    if row and "UNIQUE" in row[0]:
        c.execute("ALTER TABLE authorities RENAME TO authorities_legacy")
        c.execute(_CREATE_AUTHORITIES)
        c.execute("INSERT INTO authorities SELECT * FROM authorities_legacy")
        c.execute("DROP TABLE authorities_legacy")
    c.execute(_CREATE_AUTHORITIES)
    c.execute("CREATE INDEX IF NOT EXISTS idx_authorities_canonical "
              "ON authorities (canonical)")
    # Compound citations ("262 U.S. 390 (1923); 43 S.Ct. 625") get one row;
    # each component citation becomes an alias resolving to that row.
    c.execute(
        """CREATE TABLE IF NOT EXISTS citation_aliases (
            alias TEXT PRIMARY KEY, canonical TEXT
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
                  confirmed_by: str = "", aliases: list[str] | None = None) -> None:
    canonical = canonicalize(citation)
    c = _conn()
    # Replace semantics per (citation, name): re-adding the same capture
    # updates it; a different capture of the same citation adds a sibling row.
    c.execute("DELETE FROM authorities WHERE canonical=? AND name=?",
              (canonical, name))
    c.execute(
        """INSERT INTO authorities
           (name, citation, canonical, type, court, year, holding,
            captured_text, source_url, retrieved_date, confirmed_by)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (name, citation, canonical, type, court, year, holding,
         captured_text, source_url, retrieved_date, confirmed_by),
    )
    for alias in aliases or []:
        alias_c = canonicalize(alias)
        if alias_c != canonical:
            c.execute(
                "INSERT OR REPLACE INTO citation_aliases (alias, canonical) VALUES (?,?)",
                (alias_c, canonical),
            )
    c.commit()
    c.close()


_ROW_KEYS = ["name", "citation", "type", "court", "year", "holding",
             "captured_text", "source_url", "retrieved_date", "confirmed_by"]
_ROW_SQL = ("SELECT name, citation, type, court, year, holding, captured_text, "
            "source_url, retrieved_date, confirmed_by FROM authorities ")


def get_all_by_citation(cite: str) -> list[dict]:
    """Every capture of this citation (directly or via alias), most complete
    text first."""
    key = canonicalize(cite)
    c = _conn()
    rows = c.execute(
        _ROW_SQL + "WHERE canonical = ? OR canonical = "
        "(SELECT canonical FROM citation_aliases WHERE alias = ?) "
        "ORDER BY LENGTH(captured_text) DESC",
        (key, key),
    ).fetchall()
    c.close()
    return [dict(zip(_ROW_KEYS, r)) for r in rows]


def get_by_citation(cite: str) -> dict | None:
    rows = get_all_by_citation(cite)
    return rows[0] if rows else None


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
        rows = get_all_by_citation(cite)
        if not rows:
            unknown.append(cite)
        elif not any(r["confirmed_by"] for r in rows):
            unconfirmed.append(cite)
        else:
            known.append(cite)
    return {"known": known, "unconfirmed": unconfirmed, "unknown": unknown}
