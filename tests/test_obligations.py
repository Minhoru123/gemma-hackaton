import config
from app import obligations


def _setup(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    obligations.init()


def test_warnings_urgency_and_ordering(tmp_path):
    _setup(tmp_path)
    obligations.add("File opposition", due_date="2026-07-10", rule_cite="r1")
    obligations.add("File reply", due_date="2026-07-22")
    obligations.add("Review order", due_date="2026-09-01")
    obligations.add("No date yet")
    w = obligations.warnings(today="2026-07-18")
    assert [x["urgency"] for x in w] == ["overdue", "due_soon", "open", "open"]
    assert w[0]["label"] == "File opposition"


def test_try_satisfy_matches_doc_type(tmp_path):
    _setup(tmp_path)
    obligations.add("File opposition to their_msj.pdf", satisfied_by="opposition")
    obligations.add("File reply", satisfied_by="reply")
    satisfied = obligations.try_satisfy("opposition")
    assert satisfied == ["File opposition to their_msj.pdf"]
    assert [o["label"] for o in obligations.list_open()] == ["File reply"]


def test_manual_satisfy(tmp_path):
    _setup(tmp_path)
    oid = obligations.add("Submit exhibit list")
    obligations.satisfy(oid)
    assert obligations.list_open() == []
