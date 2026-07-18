import config
from app import deadlines, obligations, timeline


def test_motion_triggers_presumptive_opposition_deadline(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    obligations.init()
    timeline.init()
    created = deadlines.apply("motion", "2026-07-01", "their_msj.pdf")
    assert len(created) == 1
    assert created[0]["due_date"] == "2026-07-15"  # 14 days later
    ob = obligations.list_open()[0]
    assert ob["label"] == "File opposition to their_msj.pdf"
    assert ob["presumptive"] == 1
    assert ob["satisfied_by"] == "opposition"
    assert ob["rule_cite"]
    events = timeline.list_events()
    assert events[0]["kind"] == "presumptive_deadline"
    assert "PRESUMPTIVE" in events[0]["label"]
    assert "confirm with the court or your attorney" in events[0]["label"]


def test_unknown_doc_type_triggers_nothing(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    obligations.init()
    timeline.init()
    assert deadlines.apply("letter", "2026-07-01", "letter.pdf") == []
    assert obligations.list_open() == []
