"""Seed a coverage-map checklist from an opposing/parent filing.

    python scripts/seed_coverage_map.py their_motion.pdf coverage_map.md
"""
import os
import sys
sys.path.insert(0, os.path.abspath("."))
from app import ingest, coverage  # noqa: E402


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    parent, out = sys.argv[1], sys.argv[2]
    text = ingest.extract_text(parent)
    content = coverage.seed_map(text, os.path.basename(parent))
    with open(out, "w", encoding="utf-8") as f:
        f.write(content)
    items = content.count("- [ ]")
    print(f"seeded {items} contentions -> {out}")


if __name__ == "__main__":
    main()
