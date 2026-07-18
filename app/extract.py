import json
import re
from app import ollama_client

_PROMPT = (
    "Extract key facts from this legal document. Return ONLY a JSON object with keys: "
    "summary (one sentence), parties, deadline, amount, action_required, "
    "risks (array of short plain-English risk warnings, e.g. missed-deadline consequences). "
    "Use \"Not stated\" for anything not present. Document:\n\n{doc}"
)

_FIELDS = ["summary", "parties", "deadline", "amount", "action_required"]


def _extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def key_facts(document_text: str) -> dict:
    raw = ollama_client.generate(_PROMPT.format(doc=document_text[:4000]))
    data = _extract_json(raw)
    out = {f: str(data.get(f, "Not stated")) or "Not stated" for f in _FIELDS}
    risks = data.get("risks", [])
    out["risks"] = [str(r) for r in risks] if isinstance(risks, list) else []
    return out
