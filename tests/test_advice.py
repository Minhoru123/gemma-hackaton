import json
import config
from app import advice, questions, store, ollama_client


def _setup(tmp_path, monkeypatch, search_hits, verdicts):
    config.DB_PATH = str(tmp_path / "t.db")
    questions.init()
    monkeypatch.setattr(store, "search", lambda q, k=2: search_hits)
    responses = iter(verdicts)

    def fake_generate(prompt, system=""):
        if "discrete checkable claims" in prompt:
            return json.dumps({"claims": ["You have 14 days to respond."]})
        return json.dumps(next(responses))
    monkeypatch.setattr(ollama_client, "generate", fake_generate)


def test_matching_claim_creates_no_question(tmp_path, monkeypatch):
    hits = [{"text": "A response must be filed within 14 days.",
             "source": "URCP 7", "kind": "authority", "score": 0.8}]
    _setup(tmp_path, monkeypatch, hits,
           [{"verdict": "matches", "quote": "A response must be filed within 14 days."}])
    result = advice.check("advice text")
    assert result["claims"][0]["verdict"] == "matches"
    assert result["claims"][0]["source"] == "URCP 7"
    assert questions.list_open() == []


def test_conflicting_claim_queues_question(tmp_path, monkeypatch):
    hits = [{"text": "A response must be filed within 7 days.",
             "source": "URCP 7", "kind": "authority", "score": 0.8}]
    _setup(tmp_path, monkeypatch, hits,
           [{"verdict": "conflicts", "quote": "within 7 days"}])
    result = advice.check("advice text")
    assert result["claims"][0]["verdict"] == "conflicts"
    qs = questions.list_open()
    assert len(qs) == 1
    assert "Ask your attorney" in qs[0]["question"]


def test_uncovered_claim_queues_question(tmp_path, monkeypatch):
    hits = [{"text": "gardening", "source": "x", "kind": "corpus", "score": 0.2}]
    _setup(tmp_path, monkeypatch, hits, [])
    result = advice.check("advice text")
    assert result["claims"][0]["verdict"] == "not_covered"
    assert len(questions.list_open()) == 1
