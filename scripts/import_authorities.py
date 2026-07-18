"""Bulk-import an existing reference library (AUTHORITIES.jsonl + _AI_TEXT
captures) into this project's authorities database.

    python scripts/import_authorities.py "/path/to/_REFERENCE_LIBRARY"
        [--embed-holdings]   # also embed name+citation+holding per authority
                             # into the search index (needs Ollama; ~minutes)
        [--embed-rules]      # also embed FULL text of statute/rule captures
                             # (needs Ollama; slower, grows the index a lot)

Provenance is preserved: rows the source library marks 'library' provenance
(user-supplied official documents) import as confirmed; web-captured rows
import with their recorded confirmed_by, or as Tier 2 (not citable) if blank.
Compound citations get an alias per component so drafts citing any reporter
form resolve. Re-running is safe (rows replace by citation).
"""
import json
import os
import sys
import argparse
sys.path.insert(0, os.path.abspath("."))
from app import authorities, ingest  # noqa: E402

LIBRARY_CONFIRMED = "library-provenance (bulk import)"


def import_row(row: dict, library_dir: str) -> dict:
    path = os.path.join(library_dir, row["ai_text"])
    captured = ""
    if os.path.exists(path):
        captured = ingest.strip_frontmatter(ingest.extract_text(path))
    confirmed = row.get("confirmed_by", "")
    if not confirmed and row.get("provenance") == "library":
        confirmed = LIBRARY_CONFIRMED
    citation = row["citation"]
    aliases = authorities.extract_citations(citation)
    authorities.add_authority(
        name=row["authority"], citation=citation, captured_text=captured,
        type=row.get("type", "case"), court=row.get("court", ""),
        year=str(row.get("year", "")), holding=row.get("holding", ""),
        source_url=row.get("source_url", ""),
        retrieved_date=row.get("retrieved", ""),
        confirmed_by=confirmed, aliases=aliases,
    )
    return {"captured": bool(captured), "confirmed": bool(confirmed),
            "aliases": len(aliases)}


def main():
    ap = argparse.ArgumentParser(description="Import a reference library.")
    ap.add_argument("library", help="path to _REFERENCE_LIBRARY "
                                    "(contains AUTHORITIES.jsonl and _AI_TEXT/)")
    ap.add_argument("--embed-holdings", action="store_true")
    ap.add_argument("--embed-rules", action="store_true")
    ap.add_argument("--fresh", action="store_true",
                    help="clear the authorities tables before importing "
                         "(also removes manually added authorities)")
    args = ap.parse_args()

    index_path = os.path.join(args.library, "AUTHORITIES.jsonl")
    with open(index_path, "r", encoding="utf-8") as f:
        rows = json.load(f)  # despite the name, a pretty-printed JSON array

    authorities.init_db()
    if args.fresh:
        import sqlite3
        import config
        c = sqlite3.connect(config.DB_PATH)
        n = c.execute("DELETE FROM authorities").rowcount
        c.execute("DELETE FROM citation_aliases")
        c.commit()
        c.close()
        print(f"--fresh: cleared {n} existing authority rows")
    stats = {"rows": 0, "with_text": 0, "confirmed": 0, "aliases": 0}
    for row in rows:
        r = import_row(row, args.library)
        stats["rows"] += 1
        stats["with_text"] += r["captured"]
        stats["confirmed"] += r["confirmed"]
        stats["aliases"] += r["aliases"]
        if stats["rows"] % 200 == 0:
            print(f"  …{stats['rows']}/{len(rows)}")
    print(f"imported {stats['rows']} authorities "
          f"({stats['with_text']} with captured text, "
          f"{stats['confirmed']} citable, "
          f"{stats['rows'] - stats['confirmed']} Tier 2 unconfirmed, "
          f"{stats['aliases']} citation aliases)")

    if args.embed_holdings or args.embed_rules:
        from app import store  # imports Ollama client — only needed here
        store.init_db()
        n = 0
        for row in rows:
            if args.embed_holdings and row.get("holding"):
                text = f"{row['authority']}, {row['citation']}: {row['holding']}"
                store.add_chunks(f"{row['authority']}, {row['citation']}",
                                 [text], kind="authority")
                n += 1
            if args.embed_rules and row.get("type") == "statute/rule":
                path = os.path.join(args.library, row["ai_text"])
                if os.path.exists(path):
                    text = ingest.strip_frontmatter(ingest.extract_text(path))
                    store.add_chunks(f"{row['authority']}, {row['citation']}",
                                     ingest.chunk_text(text), kind="authority")
                    n += 1
            if n and n % 100 == 0:
                print(f"  …embedded {n}")
        print(f"embedded {n} authorities into the search index")


if __name__ == "__main__":
    main()
