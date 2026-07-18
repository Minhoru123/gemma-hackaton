"""Process every filing dropped in the intake folder: diff citations against
the library, queue unknowns on the fetch list, move files to completed/.

    python scripts/process_intake.py
"""
import os
import sys
sys.path.insert(0, os.path.abspath("."))
import config  # noqa: E402
from app import authorities, intake  # noqa: E402


def main():
    authorities.init_db()
    os.makedirs(config.INTAKE_DIR, exist_ok=True)
    reports = intake.process_intake()
    if not reports:
        print(f"nothing waiting in {config.INTAKE_DIR}/")
        return
    for r in reports:
        print(f"{r['file']}: {len(r['known'])} known, "
              f"{len(r['unconfirmed'])} unconfirmed, "
              f"{len(r['unknown'])} unknown ({r['queued']} newly queued)")
        for cite in r["unknown"]:
            print(f"  fetch: {cite}")
    print(f"fetch list: {config.FETCH_LIST}")


if __name__ == "__main__":
    main()
