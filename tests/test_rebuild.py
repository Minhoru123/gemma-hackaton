import config
from app import timeline, cases, store, obligations, rebuild, case_events


def _setup(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    cases.init()
    store.init_db()
    timeline.init()
    obligations.init()


def test_add_event_dedupes_restated_events(tmp_path):
    _setup(tmp_path)
    assert timeline.add_event("case_event", "Hearing held", "2026-06-20") is True
    # A later document restating the same event on the same day is skipped.
    assert timeline.add_event("case_event", "hearing  held", "2026-06-20") is False
    # Same label on a different day is a different event.
    assert timeline.add_event("case_event", "Hearing held", "2026-07-20") is True
    assert len(timeline.list_events()) == 2


def test_clear_case_only_clears_active_case(tmp_path):
    _setup(tmp_path)
    timeline.add_event("filed", "Filed: a.pdf", "2026-01-01")
    first = cases.active_id()
    cases.create("Other case")
    timeline.add_event("filed", "Filed: b.pdf", "2026-02-01")
    assert timeline.clear_case() == 1
    cases.set_active(first)
    assert len(timeline.list_events()) == 1  # first case untouched


def test_rebuild_rederives_from_documents_and_obligations(tmp_path, monkeypatch):
    _setup(tmp_path)
    timeline.add_event("case_event", "Stale event from old analyzer", "2026-01-01")
    obligations.add("File opposition to mtd.pdf", trigger_source="mtd.pdf",
                    due_date="2026-07-15", rule_cite="URCP 7")
    monkeypatch.setattr(store, "list_sources",
                        lambda: [{"source": "mtd.pdf", "chunks": 2}])
    monkeypatch.setattr(store, "get_source_text",
                        lambda s: "motion text" if s == "mtd.pdf" else "")
    monkeypatch.setattr(case_events, "analyze", lambda text: {
        "doc_type": "motion", "filed_date": "2026-07-01", "filed_by": "defendant",
        "events": [{"date": "2026-06-20", "event": "Hearing held"}], "faults": []})
    stats = rebuild.rebuild_timeline()
    assert stats["events_removed"] == 1          # stale event gone
    events = timeline.list_events()
    labels = [e["label"] for e in events]
    assert "Filed: mtd.pdf (motion)" in labels
    assert "Hearing held" in labels
    assert any("File opposition to mtd.pdf" in l and "PRESUMPTIVE" in l
               for l in labels)
    assert "Stale event from old analyzer" not in labels
    # Rebuilding again changes nothing (dedupe + deterministic derivation).
    rebuild.rebuild_timeline()
    assert [e["label"] for e in timeline.list_events()] == labels
