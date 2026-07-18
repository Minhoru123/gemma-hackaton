"""Extract deadline rules from an uploaded rules-of-procedure document.
Proposal-first: extracted rules go to a PROPOSED file for human review and
only merge into the active rules table on explicit approval. Every proposed
rule must carry a quote that verbatim-matches the source text — anything the
model paraphrased or invented is dropped mechanically."""

import json
import os
import config
from app import ollama_client
from app.extract import _extract_json
from app.verify import _norm
from app.case_events import DOC_TYPES

_CHUNK = 4000

_PROMPT = (
    "This is an excerpt from court rules of procedure. Find every rule that "
    "sets a DEADLINE IN DAYS triggered by a filing or service of a document. "
    "Return ONLY a JSON object {{\"rules\": [...]}} where each rule is:\n"
    "trigger_doc_type (the filing that starts the clock — one of: motion, "
    "opposition, reply, order, notice, other),\n"
    "obligation (what must be filed, phrased like 'File opposition to "
    "{{source}}'),\n"
    "satisfied_by (the doc type that satisfies it — one of: motion, "
    "opposition, reply, notice, other — or \"\"),\n"
    "days (integer),\n"
    "rule_cite (the rule number, e.g. 'URCP 7(e)'),\n"
    "quote (the EXACT sentence from the excerpt that states the period — "
    "copy it verbatim).\n"
    "Empty array if this excerpt sets no such deadline.\n\n"
    "Excerpt:\n\n{chunk}"
)


def _valid(rule: dict, source_chunk: str) -> bool:
    if not isinstance(rule, dict):
        return False
    days = rule.get("days")
    if not (isinstance(days, int) and 1 <= days <= 365):
        return False
    if rule.get("trigger_doc_type") not in DOC_TYPES:
        return False
    if rule.get("satisfied_by", "") not in DOC_TYPES + [""]:
        return False
    if not (rule.get("obligation") and rule.get("rule_cite")):
        return False
    # The anti-hallucination gate: the quote must appear in the source text.
    quote = str(rule.get("quote", ""))
    return bool(quote) and _norm(quote) in _norm(source_chunk)


def extract_from_text(rules_text: str) -> list[dict]:
    """Run extraction over the whole rules document, chunk by chunk. Only
    rules whose quotes verbatim-match the source survive."""
    proposed, seen = [], set()
    for start in range(0, len(rules_text), _CHUNK):
        chunk = rules_text[start:start + _CHUNK]
        raw = ollama_client.generate(_PROMPT.format(chunk=chunk))
        data = _extract_json(raw)
        for rule in data.get("rules", []) if isinstance(data.get("rules"), list) else []:
            if not _valid(rule, chunk):
                continue
            key = (rule["trigger_doc_type"], str(rule["obligation"]).lower())
            if key in seen:
                continue
            seen.add(key)
            proposed.append({
                "trigger_doc_type": rule["trigger_doc_type"],
                "obligation": str(rule["obligation"]),
                "satisfied_by": rule.get("satisfied_by", ""),
                "days": rule["days"],
                "rule_cite": str(rule["rule_cite"]),
                "quote": str(rule["quote"]),
            })
    return proposed


def save_proposed(rules: list[dict]) -> str:
    path = config.DEADLINE_RULES_PROPOSED
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2)
    return path


def load_proposed() -> list[dict]:
    path = config.DEADLINE_RULES_PROPOSED
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def approve() -> dict:
    """Merge the (human-reviewed) proposed rules into the active rules table,
    deduplicating against what is already there. Clears the proposed file."""
    proposed = load_proposed()
    if not proposed:
        return {"merged": 0, "skipped": 0}
    with open(config.DEADLINE_RULES, "r", encoding="utf-8") as f:
        active = json.load(f)
    existing = {(r["trigger_doc_type"], r["obligation"].lower()) for r in active}
    merged = skipped = 0
    for rule in proposed:
        key = (rule["trigger_doc_type"], rule["obligation"].lower())
        if key in existing:
            skipped += 1
            continue
        existing.add(key)
        active.append(rule)
        merged += 1
    with open(config.DEADLINE_RULES, "w", encoding="utf-8") as f:
        json.dump(active, f, indent=2)
    os.remove(config.DEADLINE_RULES_PROPOSED)
    return {"merged": merged, "skipped": skipped}
