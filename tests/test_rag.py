import config
from app import store, rag


def test_low_relevance_triggers_i_dont_know(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    config.MIN_SCORE = 0.99  # force the guardrail
    store.init_db()
    store.add_chunks("doc", ["Unrelated content about gardening."], kind="corpus")
    result = rag.answer("What is my court deadline?")
    assert result["grounded"] is False
    assert "don't have information" in result["answer"]
