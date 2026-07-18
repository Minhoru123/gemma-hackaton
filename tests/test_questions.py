import config
from app import questions


def test_add_list_resolve_and_dedupe(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    questions.init()
    assert questions.add("Why was the opposition late?", source="order.pdf") is True
    assert questions.add("Why was the opposition late?") is False  # dedupe
    assert questions.add("What is the hearing about?") is True
    open_qs = questions.list_open()
    assert len(open_qs) == 2
    questions.resolve(open_qs[0]["id"])
    assert len(questions.list_open()) == 1
