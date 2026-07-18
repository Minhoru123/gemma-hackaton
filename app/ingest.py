from pypdf import PdfReader
import config


def extract_text(path: str) -> str:
    lower = path.lower()
    if lower.endswith(".pdf"):
        reader = PdfReader(path)
        parts = [(page.extract_text() or "") for page in reader.pages]
        return "\n".join(parts).strip()
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()


def strip_frontmatter(text: str) -> str:
    """Remove a leading YAML frontmatter block (--- ... ---) if present."""
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text


def chunk_text(text: str) -> list[str]:
    size, overlap = config.CHUNK_CHARS, config.CHUNK_OVERLAP
    text = " ".join(text.split())  # normalize whitespace
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks
