import config
from app import party, cases, store, jurisdiction


def _setup(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    cases.init()
    store.init_db()


def test_role_is_per_case(tmp_path):
    _setup(tmp_path)
    party.set("plaintiff")
    assert party.get() == "plaintiff"
    cases.create("Second case")
    assert party.get() == ""          # new case: not asked yet
    party.set("defendant")
    assert party.get() == "defendant"
    cases.set_active(1)
    assert party.get() == "plaintiff"  # first case remembers its own role


def test_invalid_role_ignored(tmp_path):
    _setup(tmp_path)
    party.set("judge")
    assert party.get() == ""


def test_origin_relative_to_user(tmp_path):
    _setup(tmp_path)
    assert party.origin("plaintiff") == ""   # role unknown -> unknown origin
    party.set("plaintiff")
    assert party.origin("plaintiff") == "user"
    assert party.origin("defendant") == "opponent"
    assert party.origin("court") == ""
    assert party.origin("") == ""


def test_side_of_phrases():
    assert party.side_of("Plaintiff's counsel") == "plaintiff"
    assert party.side_of("the Respondent") == "defendant"
    assert party.side_of("Petitioner Jordan Rivera") == "plaintiff"
    assert party.side_of("the court clerk") == ""
    assert party.side_of("Plaintiff and Defendant jointly") == ""


def test_jurisdiction_is_per_case_with_legacy_migration(tmp_path):
    _setup(tmp_path)
    store.set_meta("jurisdiction", "federal")  # legacy global key
    jurisdiction.migrate_legacy()
    assert jurisdiction.get_case() == "federal"
    assert store.get_meta("jurisdiction") == ""  # legacy key retired
    cases.create("State case")
    assert jurisdiction.get_case() == ""         # not inherited by new case
    jurisdiction.set_case("utah")
    assert jurisdiction.get_case() == "utah"
    cases.set_active(1)
    assert jurisdiction.get_case() == "federal"
