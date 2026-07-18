import config
from app import cases, store, timeline, questions, obligations


def _fresh(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    cases.init()
    store.init_db()
    timeline.init()
    questions.init()
    obligations.init()


def test_init_creates_default_active_case(tmp_path):
    _fresh(tmp_path)
    all_cases = cases.list_all()
    assert len(all_cases) == 1
    assert all_cases[0]["name"] == "My case"
    assert all_cases[0]["is_active"] is True
    assert cases.active_id() == all_cases[0]["id"]


def test_create_switches_active_and_blank_name_falls_back(tmp_path):
    _fresh(tmp_path)
    a = cases.active_id()
    b = cases.create("Second matter")
    assert cases.active_id() == b and b != a
    c = cases.create("   ")  # blank -> "Untitled case"
    assert cases.list_all()[0]["name"] == "Untitled case"
    assert cases.active_id() == c


def test_set_active_leaves_exactly_one_active(tmp_path):
    _fresh(tmp_path)
    a = cases.active_id()
    b = cases.create("B")
    cases.set_active(a)
    actives = [c for c in cases.list_all() if c["is_active"]]
    assert len(actives) == 1 and actives[0]["id"] == a


def test_set_active_nonexistent_is_noop(tmp_path):
    _fresh(tmp_path)
    a = cases.active_id()
    cases.set_active(9999)  # doesn't exist
    assert cases.active_id() == a  # unchanged


def test_uploads_timeline_questions_obligations_isolated_per_case(tmp_path):
    _fresh(tmp_path)
    a = cases.active_id()
    store.add_chunks("docA.txt", ["The response deadline is twenty days after service."], kind="upload")
    timeline.add_event("filed", "Filed: docA.txt (notice)", "2026-08-03")
    questions.add("Ask about docA", source="docA.txt")
    obligations.add("Respond to petition", due_date="2026-08-03")

    b = cases.create("Case B")
    # Case B sees nothing from A
    assert store.list_sources() == []
    assert timeline.list_events() == []
    assert questions.list_open() == []
    assert obligations.warnings() == []

    # Switch back to A: everything returns
    cases.set_active(a)
    assert [d["source"] for d in store.list_sources()] == ["docA.txt"]
    assert len(timeline.list_events()) == 1
    assert len(questions.list_open()) == 1
    assert len(obligations.warnings()) == 1


def test_same_question_allowed_in_two_cases(tmp_path):
    _fresh(tmp_path)
    assert questions.add("Same question?", source="user") is True
    cases.create("Other")
    # Same text, different case -> should be added, not deduped away
    assert questions.add("Same question?", source="user") is True


def test_remove_source_deletes_doc_chunks_timeline_and_questions(tmp_path):
    _fresh(tmp_path)
    store.add_chunks("keep.txt", ["Keep this content about deadlines."], kind="upload")
    store.add_chunks("drop.txt", ["Drop this content about hearings."], kind="upload")
    timeline.add_event("filed", "Filed: drop.txt (notice)", "2026-08-03")
    questions.add("Flagged from drop", source="drop.txt")
    questions.add("My own note", source="user")

    removed = store.remove_source("drop.txt")
    timeline.remove_by_source("drop.txt")
    questions.remove_by_source("drop.txt")

    assert removed == 1
    sources = [d["source"] for d in store.list_sources()]
    assert sources == ["keep.txt"]                       # only drop.txt gone
    assert timeline.list_events() == []                  # its event removed
    qs = [q["question"] for q in questions.list_open()]
    assert "My own note" in qs                           # user note kept
    assert "Flagged from drop" not in qs                 # its flag removed


def test_corpus_chunks_are_shared_across_cases(tmp_path):
    _fresh(tmp_path)
    # Corpus (reference) chunks are not tied to a case.
    store.add_chunks("rights.md", ["You have twenty days to respond after service."], kind="corpus")
    a_hits = store.search("how long to respond")
    cases.create("New case")
    b_hits = store.search("how long to respond")
    # Both cases can retrieve the shared corpus chunk.
    assert any(h["source"] == "rights.md" for h in a_hits)
    assert any(h["source"] == "rights.md" for h in b_hits)
