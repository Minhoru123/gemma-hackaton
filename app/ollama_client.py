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
    """Remove E2B reasoning-model channel scaffolding, keep the final answer."""
    text = _THOUGHT_RE.sub("", text)
    text = _TAG_RE.sub("", text)
    # Some builds prefix the final answer with 'final'/'answer' channel words.
    text = re.sub(r"^\s*(final|answer)\s*", "", text, flags=re.IGNORECASE)
    return text.strip()


def embed(text: str) -> list[float]:
    d = _post("/api/embeddings", {"model": config.EMBED_MODEL, "prompt": text})
    return d["embedding"]


def generate(prompt: str, system: str = "") -> str:
    payload = {"model": config.GEN_MODEL, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system
    d = _post("/api/generate", payload)
    return strip_scaffold(d.get("response", ""))


def warmup() -> None:
    try:
        generate("Reply with the single word: ready.")
    except Exception:
        pass
