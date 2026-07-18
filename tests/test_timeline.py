import config
from app import timeline


def test_events_sorted_by_when(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    timeline.init()
    timeline.add_event("case_date", "Hearing", "2026-08-03")
    timeline.add_event("upload", "Uploaded notice", "2026-07-18")
    events = timeline.list_events()
    assert [e["when"] for e in events] == ["2026-07-18", "2026-08-03"]
