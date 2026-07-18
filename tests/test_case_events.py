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
        "faults": [
            {"category": "untimely-filing",
             "quote": "Plaintiff's opposition was untimely.",
             "who": "Plaintiff's counsel", "issue": "untimely filing"},
            {"category": "not-a-real-category",
             "quote": "Counsel failed to appear at the hearing.",
             "who": "Plaintiff's counsel", "issue": "missed hearing"},
            {"category": "waiver-forfeiture", "who": "x", "issue": "no quote -> dropped"},
        ],
    }))
    a = case_events.analyze("IT IS HEREBY ORDERED that the motion is granted.")
    assert a["doc_type"] == "order"
    assert a["filed_date"] == "2026-06-30"
    assert [e["event"] for e in a["events"]] == ["Motion filed", "Hearing held"]
    assert len(a["faults"]) == 2
    assert a["faults"][0]["category"] == "untimely-filing"
    assert a["faults"][1]["category"] == "other-error"  # unknown category coerced


def test_analyze_defaults_on_garbage(monkeypatch):
    monkeypatch.setattr(ollama_client, "generate",
                        lambda prompt, system="": "not json at all")
    a = case_events.analyze("text with no operative language")
    assert a == {"doc_type": "other", "filed_date": "", "events": [],
                 "faults": []}


def test_content_signals_override_title_based_classification(monkeypatch):
    # The model (misled by the title) says "notice", but the body moves for relief.
    monkeypatch.setattr(ollama_client, "generate", _fake_generate({
        "doc_type": "notice", "filed_date": "", "events": [], "faults": []}))
    a = case_events.analyze(
        "NOTICE OF MOTION\n\nDefendant hereby moves for summary judgment.")
    assert a["doc_type"] == "motion"


def test_content_signal_priority_order_beats_motion():
    text = ("The court considered defendant's motion. Defendant moves for "
            "dismissal. IT IS HEREBY ORDERED that the motion is DENIED.")
    assert case_events.classify_by_content(text) == "order"


def test_no_signal_returns_empty():
    assert case_events.classify_by_content(
        "Please take notice that a hearing is set for August 3.") == ""
