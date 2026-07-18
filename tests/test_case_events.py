import json
from app import case_events, ollama_client


def _fake_generate(response):
    def fake(prompt, system=""):
        return json.dumps(response)
    return fake


def test_analyze_parses_full_response(monkeypatch):
    monkeypatch.setattr(ollama_client, "generate", _fake_generate({
        "doc_type": "Order",
        "filed_date": "2026-06-30",
        "events": [
            {"date": "2026-06-01", "event": "Motion filed"},
            {"date": "not-a-date", "event": "dropped"},
            {"date": "2026-06-20", "event": "Hearing held"},
        ],
        "fault": {"found": True,
                  "quote": "Plaintiff's opposition was untimely.",
                  "who": "Plaintiff's counsel", "issue": "untimely filing"},
    }))
    a = case_events.analyze("some order text")
    assert a["doc_type"] == "order"
    assert a["filed_date"] == "2026-06-30"
    assert [e["event"] for e in a["events"]] == ["Motion filed", "Hearing held"]
    assert a["fault"]["found"] is True
    assert "untimely" in a["fault"]["quote"]


def test_analyze_defaults_on_garbage(monkeypatch):
    monkeypatch.setattr(ollama_client, "generate",
                        lambda prompt, system="": "not json at all")
    a = case_events.analyze("text")
    assert a == {"doc_type": "other", "filed_date": "", "events": [],
                 "fault": {"found": False, "quote": "", "who": "", "issue": ""}}


def test_unknown_doc_type_becomes_other(monkeypatch):
    monkeypatch.setattr(ollama_client, "generate", _fake_generate({
        "doc_type": "subpoena", "filed_date": "", "events": [], "fault": {}}))
    assert case_events.analyze("text")["doc_type"] == "other"
