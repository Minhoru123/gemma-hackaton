import json
import re
import urllib.request
import config

_THOUGHT_RE = re.compile(r"<\|channel\|?>thought.*?(?=<\|)", re.DOTALL)
_TAG_RE = re.compile(r"<\|[^>]*\|?>")


def _post(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        config.OLLAMA_URL + path, data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def strip_scaffold(text: str) -> str:
    """Remove reasoning-model channel scaffolding, keep the final answer."""
    text = _THOUGHT_RE.sub("", text)
    text = _TAG_RE.sub("", text)
    # Some builds prefix the final answer with 'final'/'answer' channel words.
    text = re.sub(r"^\s*(final|answer)\s*", "", text, flags=re.IGNORECASE)
    return text.strip()


_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__", re.DOTALL)
_MD_ITALIC_STAR_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")
_MD_ITALIC_UND_RE = re.compile(r"(?<![\w])_([^_\n]+)_(?![\w])")


def strip_markdown(text: str) -> str:
    """Flatten markdown into plain prose for non-technical readers. Applied to
    user-facing prose only — never to JSON-bearing model output."""
    text = re.sub(r"\\([_*#\[\]()~`>+\-.!])", r"\1", text)     # \_ -> _
    text = _MD_BOLD_RE.sub(lambda m: m.group(1) or m.group(2), text)
    text = _MD_ITALIC_STAR_RE.sub(r"\1", text)
    text = _MD_ITALIC_UND_RE.sub(r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)  # headings
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)    # blockquotes
    text = re.sub(r"^(\s*)[*+\-•]\s+", r"\1• ", text, flags=re.MULTILINE)
    text = re.sub(r"`([^`\n]*)`", r"\1", text)                  # inline code
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def embed(text: str) -> list[float]:
    d = _post("/api/embeddings", {"model": config.EMBED_MODEL, "prompt": text})
    return d["embedding"]


def generate(prompt: str, system: str = "") -> str:
    # think=False disables chain-of-thought on reasoning-capable model builds so
    # they return only the final answer. strip_scaffold stays as a fallback in
    # case a model build ignores the flag.
    payload = {"model": config.GEN_MODEL, "prompt": prompt,
               "stream": False, "think": False}
    if system:
        payload["system"] = system
    d = _post("/api/generate", payload)
    return strip_scaffold(d.get("response", ""))


def warmup() -> None:
    try:
        generate("Reply with the single word: ready.")
    except Exception:
        pass
