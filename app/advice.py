"""Second-opinion lane: cross-check statements in legal advice against
captured text (the rights corpus, uploaded case documents, and captured
authorities). The honest output per claim is 'matches / conflicts with / not
covered by the captured text', with the text quoted — never 'your lawyer is
right/wrong'. Conflicts and gaps become ask-your-attorney questions."""

import config
from app import store, ollama_client, questions
from app.extract import _extract_json

_CLAIMS_PROMPT = (
    "This is advice from a lawyer to their client. List the discrete checkable "
    "claims it makes about rules, deadlines, required actions, or the state of "
    "the case. Return ONLY a JSON object {{\"claims\": [\"...\"]}} with at most "
    "8 short claims, each in the advice's own words as nearly as possible.\n\n"
    "Advice:\n\n{advice}"
)

_VERDICT_PROMPT = (
    "Compare this claim from legal advice against the captured reference text "
    "below. Return ONLY a JSON object {{\"verdict\": \"matches\" or \"conflicts\" "
    "or \"unclear\", \"quote\": the single sentence from the reference text most "
    "relevant to the claim}}. Say \"matches\" only if the reference text supports "
    "the claim, \"conflicts\" only if it contradicts it.\n\n"
    "Claim: {claim}\n\nReference text:\n{context}"
)

NOT_COVERED = "not_covered"


def _extract_claims(advice_text: str) -> list[str]:
    raw = ollama_client.generate(_CLAIMS_PROMPT.format(advice=advice_text[:6000]))
    data = _extract_json(raw)
    claims = data.get("claims", [])
    return [str(c) for c in claims if str(c).strip()] if isinstance(claims, list) else []


def _check_claim(claim: str) -> dict:
    hits = store.search(claim, k=2)
    if not hits or hits[0]["score"] < config.MIN_SCORE:
        return {"claim": claim, "verdict": NOT_COVERED, "quote": "", "source": ""}
    context = "\n\n".join(h["text"] for h in hits)
    raw = ollama_client.generate(_VERDICT_PROMPT.format(claim=claim, context=context))
    data = _extract_json(raw)
    verdict = str(data.get("verdict", "unclear")).lower()
    if verdict not in ("matches", "conflicts", "unclear"):
        verdict = "unclear"
    return {"claim": claim, "verdict": verdict,
            "quote": str(data.get("quote", "")), "source": hits[0]["source"]}


def check(advice_text: str) -> dict:
    """Cross-check each claim in the advice; queue conflicts and gaps as
    ask-your-attorney questions."""
    results = [_check_claim(c) for c in _extract_claims(advice_text)]
    for r in results:
        if r["verdict"] == "conflicts":
            questions.add(
                f"The advice says: \"{r['claim']}\" — but the captured text of "
                f"{r['source']} reads differently. Ask your attorney about this.",
                source="advice check", context_quote=r["quote"])
        elif r["verdict"] == NOT_COVERED:
            questions.add(
                f"The advice says: \"{r['claim']}\" — nothing captured in your "
                "library covers this. Consider asking your attorney what it is "
                "based on.", source="advice check")
    return {"claims": results,
            "note": ("Checked against captured text only. 'Matches' or "
                     "'conflicts' refers to the captured text, not to whether "
                     "the advice is legally correct.")}
