"""Intake lane: drop filings into the intake folder; each is scanned for
citations, diffed against the authorities library, and anything unknown is
queued on the fetch list for capture. Processed files move to completed/."""

import os
import shutil
import datetime
import config
from app import ingest, authorities

_FETCH_HEADER = "# Fetch list — citations to capture\n\n"


def _load_fetch_cites(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return {authorities.canonicalize(line[len("- [ ] "):].split("(seen in")[0])
                for line in f if line.startswith("- [ ] ")}


def queue_fetches(cites: list[str], source_name: str) -> int:
    """Append unknown citations to the fetch list, deduplicated. Returns how
    many were newly queued."""
    path = config.FETCH_LIST
    os.makedirs(os.path.dirname(path), exist_ok=True)
    existing = _load_fetch_cites(path)
    fresh = [c for c in cites
             if authorities.canonicalize(c) not in existing]
    if not fresh:
        return 0
    today = datetime.date.today().isoformat()
    is_new_file = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        if is_new_file:
            f.write(_FETCH_HEADER)
        for c in fresh:
            f.write(f"- [ ] {c} (seen in {source_name}, {today})\n")
    return len(fresh)


def process_file(path: str) -> dict:
    """Scan one dropped filing, queue unknown citations, move it to completed/."""
    name = os.path.basename(path)
    text = ingest.extract_text(path)
    diff = authorities.diff_citations(text)
    queued = queue_fetches(diff["unknown"], name)
    os.makedirs(config.INTAKE_DONE_DIR, exist_ok=True)
    shutil.move(path, os.path.join(config.INTAKE_DONE_DIR, name))
    return {"file": name, "known": diff["known"], "unconfirmed": diff["unconfirmed"],
            "unknown": diff["unknown"], "queued": queued}


def process_intake() -> list[dict]:
    """Process every file waiting in the intake folder."""
    folder = config.INTAKE_DIR
    if not os.path.isdir(folder):
        return []
    reports = []
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if name.startswith(".") or not os.path.isfile(path):
            continue
        reports.append(process_file(path))
    return reports
