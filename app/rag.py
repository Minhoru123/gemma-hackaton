import config
from app import store, ollama_client

DISCLAIMER = "This is general information, not legal advice."

SYSTEM = (
    "You are Case Companion, a calm assistant that explains legal documents to people "
    "handling family-law or suing-the-state cases. Use plain, reassuring language. "
    "Answer ONLY from the provided context. If the context does not contain the answer, "
    "say you don't have that information. Never invent legal facts, deadlines, or outcomes."
)

IDK = ("I don't have information about that in your documents. "
       "Please check with your lawyer or the court.")


def _build_prompt(question: str, chunks: list[dict], language: str) -> str:
    ctx = "\n\n".join(f"[Source {i+1}: {c['source']}]\n{c['text']}"
                      for i, c in enumerate(chunks))
    return (
        f"Context:\n{ctx}\n\n"
        f"Question: {question}\n\n"
        f"Answer in {language}, in plain language, citing sources like [Source 1] "
        f"when you use them. If the context lacks the answer, say you don't have it."
    )


def answer(question: str, language: str = "English") -> dict:
    hits = store.search(question)
    grounded = bool(hits) and hits[0]["score"] >= config.MIN_SCORE
    if not grounded:
        return {"answer": IDK, "sources": [], "grounded": False}
    prompt = _build_prompt(question, hits, language)
    text = ollama_client.generate(prompt, system=SYSTEM)
    return {"answer": text, "sources": hits, "grounded": True}
