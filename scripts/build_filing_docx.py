"""Build a court-ready .docx from a draft plus a caption config.

    python scripts/build_filing_docx.py draft.md caption.json out.docx

caption.json keys: court, plaintiff, defendant, case_no, judge, title.
Unresolved [[MARKERS]] render bold-on-yellow.
"""
import json
import os
import sys
sys.path.insert(0, os.path.abspath("."))
from app import filing_docx  # noqa: E402


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(2)
    draft_path, caption_path, out_path = sys.argv[1:4]
    with open(draft_path, "r", encoding="utf-8") as f:
        draft = f.read()
    with open(caption_path, "r", encoding="utf-8") as f:
        caption = json.load(f)
    filing_docx.build(draft, caption, out_path)
    print(f"built {out_path}")


if __name__ == "__main__":
    main()
