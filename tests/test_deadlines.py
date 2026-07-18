import config
from app import deadlines, obligations, timeline


def test_motion_triggers_presumptive_opposition_deadline(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    obligations.init()
    timeline.init()
    created = deadlines.apply("motion", "2026-07-01", "their_msj.pdf",
                              jurisdiction="utah")
    assert len(created) == 1
    assert created[0]["due_date"] == "2026-07-15"  # 14 days later
    ob = obligations.list_open()[0]
    assert ob["label"] == "File opposition to their_msj.pdf"
    assert ob["presumptive"] == 1
    assert ob["satisfied_by"] == "opposition"
    assert "Utah R. Civ. P." in ob["rule_cite"]
    events = timeline.list_events()
    assert events[0]["kind"] == "presumptive_deadline"
    assert "PRESUMPTIVE" in events[0]["label"]
    assert "confirm with the court or your attorney" in events[0]["label"]


def test_federal_motion_uses_federal_rules_only(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    obligations.init()
    timeline.init()
    created = deadlines.apply("motion", "2026-07-01", "their_msj.pdf",
                              jurisdiction="federal")
    assert len(created) == 1  # one rule set, never both
    assert "DUCivR" in created[0]["rule_cite"]
    assert "Utah R. Civ. P." not in created[0]["rule_cite"]


def test_state_and_federal_reply_periods_differ(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    obligations.init()
    timeline.init()
    utah = deadlines.apply("opposition", "2026-07-01", "opp.pdf",
                           jurisdiction="utah")
    fed = deadlines.apply("opposition", "2026-07-01", "opp.pdf",
                          jurisdiction="federal")
    assert utah[0]["due_date"] == "2026-07-08"   # 7 days, Utah rules
    assert fed[0]["due_date"] == "2026-07-15"    # 14 days, federal rules


def test_unknown_jurisdiction_fires_no_tagged_rules(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    obligations.init()
    timeline.init()
    assert deadlines.apply("motion", "2026-07-01", "their_msj.pdf") == []
    assert obligations.list_open() == []


def test_deadline_arithmetic_rolls_over_month_and_year(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    obligations.init()
    timeline.init()
    created = deadlines.apply("motion", "2026-12-24", "late_motion.pdf",
                              jurisdiction="utah")
    assert created[0]["due_date"] == "2027-01-07"  # 14 days across the year end


def test_invalid_filed_date_falls_back_to_today_not_crash(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    obligations.init()
    timeline.init()
    # A semantically impossible date must not reach fromisoformat and crash.
    created = deadlines.apply("motion", "2026-02-30", "bad_date.pdf",
                              jurisdiction="utah")
    assert len(created) == 1
    assert created[0]["due_date"] > "2026-07-01"  # computed from today instead


def test_deadline_is_owed_by_the_responding_side(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    obligations.init()
    timeline.init()
    # Plaintiff files a motion -> the opposition is the DEFENDANT's duty.
    created = deadlines.apply("motion", "2026-07-01", "p_motion.pdf",
                              jurisdiction="utah", filed_by="plaintiff")
    assert created[0]["owed_by"] == "defendant"
    # The plaintiff's view hides it; the defendant's view (and no view) show it.
    assert obligations.warnings(today="2026-07-02", view="plaintiff") == []
    assert len(obligations.warnings(today="2026-07-02", view="defendant")) == 1
    assert len(obligations.warnings(today="2026-07-02")) == 1
    # The timeline entry names whose deadline it is.
    labels = [e["label"] for e in timeline.list_events()]
    assert any(l.startswith("Defendant/Respondent's deadline:") for l in labels)


def test_side_aware_satisfy(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    obligations.init()
    timeline.init()
    deadlines.apply("motion", "2026-07-01", "p_motion.pdf",
                    jurisdiction="utah", filed_by="plaintiff")
    # The plaintiff filing an opposition does NOT discharge the defendant's duty.
    assert obligations.try_satisfy("opposition", filed_by="plaintiff") == []
    # The defendant's opposition does.
    satisfied = obligations.try_satisfy("opposition", filed_by="defendant")
    assert len(satisfied) == 1
    assert obligations.list_open() == []


def test_unknown_doc_type_triggers_nothing(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    obligations.init()
    timeline.init()
    assert deadlines.apply("letter", "2026-07-01", "letter.pdf",
                           jurisdiction="utah") == []
    assert obligations.list_open() == []
