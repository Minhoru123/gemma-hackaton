"""Capture an authority into the library with provenance.

    python scripts/add_authority.py --name "State v. K.T.B." \
        --citation "2020 UT 51" --file ktb.txt --type case \
        --court "Utah Supreme Court" --year 2020 \
        --source-url https://... --retrieved 2026-07-18 --confirmed-by David

Leave --confirmed-by off for web-sourced (Tier 2) captures: the row exists but
the verifier will not let a draft cite it until it is confirmed.
"""
import os
import sys
import argparse
sys.path.insert(0, os.path.abspath("."))
from app import authorities  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Add an authority to the library.")
    ap.add_argument("--name", required=True)
    ap.add_argument("--citation", required=True)
    ap.add_argument("--file", required=True, help="captured full text file")
    ap.add_argument("--type", default="case",
                    choices=["case", "statute-rule", "filing"])
    ap.add_argument("--court", default="")
    ap.add_argument("--year", default="")
    ap.add_argument("--holding", default="")
    ap.add_argument("--source-url", default="")
    ap.add_argument("--retrieved", default="")
    ap.add_argument("--confirmed-by", default="")
    ap.add_argument("--no-embed", action="store_true",
                    help="skip embedding into the search index (no Ollama needed)")
    args = ap.parse_args()

    with open(args.file, "r", encoding="utf-8") as f:
        captured = f.read()
    authorities.init_db()
    authorities.add_authority(
        name=args.name, citation=args.citation, captured_text=captured,
        type=args.type, court=args.court, year=args.year, holding=args.holding,
        source_url=args.source_url, retrieved_date=args.retrieved,
        confirmed_by=args.confirmed_by,
    )
    if not args.no_embed:
        # Embed captured text so Q&A and the advice cross-check can find it.
        from app import store, ingest
        store.init_db()
        source = f"{args.name}, {args.citation}"
        store.add_chunks(source, ingest.chunk_text(captured), kind="authority")
    status = "confirmed" if args.confirmed_by else "UNCONFIRMED (Tier 2 — not citable)"
    embedded = "skipped" if args.no_embed else "indexed for search"
    print(f"captured {args.citation} ({args.name}) — {status}; {embedded}")


if __name__ == "__main__":
    main()
