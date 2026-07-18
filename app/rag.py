import config
from app import store, ollama_client

DISCLAIMER = "This is general information, not legal advice."

SYSTEM = (
    "You are Case Companion, a calm assistant that explains legal documents to people "
    "handling family-law or suing-the-state cases. Use plain, reassuring language. "
    "Answer ONLY from the provided context. Summarizing, explaining, or giving an "
    "overview of the provided context IS answering from it — do that willingly. "
    "If the context does not contain the answer, "
    "say you don't have that information. Never invent legal facts, deadlines, or outcomes. "
    "Write in plain sentences and short paragraphs — no markdown formatting: "
    "no asterisks, bold, bullet symbols, headings, or backslashes."
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
    text = ollama_client.strip_markdown(ollama_client.generate(prompt, system=SYSTEM))
    return {"answer": text, "sources": hits, "grounded": True}


_SUMMARY_CHARS = 16000  # how much of a document the summary prompt sees

_SUMMARY_PROMPT = (
    "Explain this legal document in plain, calm language for the person it "
    "affects. Cover: what kind of document it is, who filed it and what they "
    "are asking for, the key dates or deadlines it mentions, and what it means "
    "for the reader. Base every statement ONLY on the document text below; if "
    "something is not stated, do not guess.\n\n"
    "Answer in {language}.\n\nDocument: {name}\n\n{text}"
)


def summarize_document(source: str, language: str = "English") -> dict:
    """Whole-document explanation — bypasses chunk retrieval entirely so
    summaries reflect the document, not its 4 best-matching fragments."""
    text = store.get_source_text(source)
    if not text:
        return {"summary": "", "found": False}
    prompt = _SUMMARY_PROMPT.format(language=language, name=source,
                                    text=text[:_SUMMARY_CHARS])
    summary = ollama_client.strip_markdown(
        ollama_client.generate(prompt, system=SYSTEM))
    return {"summary": summary, "found": True}
