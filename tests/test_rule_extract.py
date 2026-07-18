import json
import config
from app import rule_extract, ollama_client

RULE_TEXT = ("Rule 7. Pleadings allowed. (e) Time to respond. A memorandum "
             "opposing a motion must be filed within 14 days after the motion "
             "is filed. A reply memorandum must be filed within 7 days after "
             "the opposing memorandum is filed.")


def test_extraction_keeps_verbatim_quotes_only(monkeypatch):
    monkeypatch.setattr(ollama_client, "generate", lambda prompt, system="": json.dumps({
        "rules": [
            {"trigger_doc_type": "motion",
             "obligation": "File opposition to {source}",
             "satisfied_by": "opposition", "days": 14, "rule_cite": "URCP 7(e)",
             "quote": "A memorandum opposing a motion must be filed within 14 "
                      "days after the motion is filed."},
            {"trigger_doc_type": "opposition",
             "obligation": "File reply to {source}",
             "satisfied_by": "reply", "days": 7, "rule_cite": "URCP 7(e)",
             "quote": "THIS SENTENCE IS NOT IN THE SOURCE TEXT."},
            {"trigger_doc_type": "motion",
             "obligation": "Bad days", "satisfied_by": "", "days": "fourteen",
             "rule_cite": "URCP 7", "quote": "A memorandum opposing a motion"},
        ]}))
    rules = rule_extract.extract_from_text(RULE_TEXT)
    assert len(rules) == 1  # hallucinated quote and non-int days dropped
    assert rules[0]["trigger_doc_type"] == "motion"
    assert rules[0]["days"] == 14


def test_save_review_approve_merges_and_dedupes(tmp_path, monkeypatch):
    config.DEADLINE_RULES = str(tmp_path / "active.json")
    config.DEADLINE_RULES_PROPOSED = str(tmp_path / "proposed.json")
    active = [{"trigger_doc_type": "motion",
               "obligation": "File opposition to {source}",
               "satisfied_by": "opposition", "days": 14, "rule_cite": "old"}]
    with open(config.DEADLINE_RULES, "w") as f:
        json.dump(active, f)
    rule_extract.save_proposed([
        {"trigger_doc_type": "motion", "obligation": "File opposition to {source}",
         "satisfied_by": "opposition", "days": 14, "rule_cite": "URCP 7(e)",
         "quote": "q"},  # duplicate of active -> skipped
        {"trigger_doc_type": "opposition", "obligation": "File reply to {source}",
         "satisfied_by": "reply", "days": 7, "rule_cite": "URCP 7(e)",
         "quote": "q2"},  # new -> merged
    ])
    result = rule_extract.approve()
    assert result == {"merged": 1, "skipped": 1}
    with open(config.DEADLINE_RULES) as f:
        merged = json.load(f)
    assert len(merged) == 2
    assert rule_extract.load_proposed() == []  # staging cleared


def test_approve_with_nothing_proposed(tmp_path):
    config.DEADLINE_RULES_PROPOSED = str(tmp_path / "none.json")
    assert rule_extract.approve() == {"merged": 0, "skipped": 0}
