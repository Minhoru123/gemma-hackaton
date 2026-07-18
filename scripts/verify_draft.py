"""Verify a draft against the authorities library. Exit nonzero on any hard
failure so this can gate a filing.

    python scripts/verify_draft.py draft.md [--coverage coverage_map.md]
"""
import os
import sys
import argparse
sys.path.insert(0, os.path.abspath("."))
from app import authorities, verify  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Mechanically verify a draft.")
    ap.add_argument("draft", help="path to the draft text/markdown file")
    ap.add_argument("--coverage", help="coverage map to gate on", default="")
    args = ap.parse_args()

    authorities.init_db()
    with open(args.draft, "r", encoding="utf-8") as f:
        text = f.read()
    coverage_text = ""
    if args.coverage:
        with open(args.coverage, "r", encoding="utf-8") as f:
            coverage_text = f.read()

    report = verify.verify_draft(text, coverage_text)
    print(verify.format_report(report))
    sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
