import config
from app import store


def test_add_and_search_ranks_relevant_chunk_first(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    store.init_db()
    store.add_chunks("doc", [
        "The response deadline is twenty days after service.",
        "The cafeteria serves lunch at noon on weekdays.",
    ], kind="corpus")
    results = store.search("How many days do I have to respond?", k=2)
    assert results[0]["text"].lower().startswith("the response deadline")
    assert results[0]["score"] > results[1]["score"]
