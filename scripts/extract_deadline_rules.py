"""Extract deadline rules from a rules-of-procedure document (e.g. the Utah
Rules of Civil Procedure), proposal-first:

    python scripts/extract_deadline_rules.py urcp.pdf
        -> writes deadline_rules_proposed.json (review it: each rule carries
           the verbatim quote it was extracted from — check days and cites)

    python scripts/extract_deadline_rules.py --approve
        -> merges the reviewed proposed rules into deadline_rules.json

Rules whose quotes do not verbatim-match the source are dropped automatically.
All resulting deadlines remain PRESUMPTIVE in the app.
"""
import os
import sys
sys.path.insert(0, os.path.abspath("."))
import config  # noqa: E402
from app import ingest, rule_extract  # noqa: E402


def main():
    if "--approve" in sys.argv:
        result = rule_extract.approve()
        print(f"merged {result['merged']} rules into {config.DEADLINE_RULES} "
              f"({result['skipped']} duplicates skipped)")
        return
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    text = ingest.extract_text(sys.argv[1])
    print(f"scanning {len(text)} chars of rules text (model pass per "
          f"{rule_extract._CHUNK}-char excerpt)…")
    proposed = rule_extract.extract_from_text(text)
    path = rule_extract.save_proposed(proposed)
    print(f"proposed {len(proposed)} rules -> {path}")
    for r in proposed:
        print(f"  [{r['rule_cite']}] {r['trigger_doc_type']} -> "
              f"{r['obligation']} in {r['days']} days")
    print("review the file (edit or delete entries), then re-run with --approve")


if __name__ == "__main__":
    main()
