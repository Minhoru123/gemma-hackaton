"""Rebuild the active case's timeline from scratch: re-analyze every stored
document (so later uploads — and analyzer improvements — inform the whole
timeline, not just the documents added after them), then re-derive the
presumptive-deadline entries from the obligations record. Deduplication in
timeline.add_event collapses events that several documents restate."""

import datetime
from app import store, timeline, case_events, obligations, deadlines, dates


def rebuild_timeline() -> dict:
    removed = timeline.clear_case()
    docs = store.list_sources()
    added = 0
    for d in docs:
        text = store.get_source_text(d["source"])
        if not text:
            continue
        analysis = case_events.analyze(text)
        filed = (analysis["filed_date"] or dates.find_date(text[-3000:])
                 or dates.find_date(text) or datetime.date.today().isoformat())
        added += timeline.add_event(
            "filed", f"Filed: {d['source']} ({analysis['doc_type']})", filed,
            source=d["source"])
        for ev in analysis["events"]:
            added += timeline.add_event("case_event", ev["event"], ev["date"],
                                        source=d["source"])
    for ob in obligations.list_all():
        if not ob["due_date"]:
            continue
        label = (deadlines.deadline_label(ob["label"], ob["owed_by"],
                                          ob["rule_cite"])
                 if ob["presumptive"] else ob["label"])
        added += timeline.add_event("presumptive_deadline", label,
                                    ob["due_date"], source=ob["trigger_source"])
    return {"documents": len(docs), "events_removed": removed,
            "events_added": added}
