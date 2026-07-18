import config
from app import store, rag, ingest, ollama_client, cases


def test_get_source_text_reconstructs_without_overlap_duplication(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    cases.init()
    store.init_db()
    text = " ".join(f"word{i}" for i in range(400))  # ~2 chunks with overlap
    chunks = ingest.chunk_text(text)
    assert len(chunks) > 1
    store.add_chunks("doc.txt", chunks, kind="upload")
    rebuilt = store.get_source_text("doc.txt")
    assert rebuilt == text  # overlap trimmed exactly, no duplicated seams


def test_summarize_document_uses_full_text(tmp_path, monkeypatch):
    config.DB_PATH = str(tmp_path / "t.db")
    seen = {}
    monkeypatch.setattr(store, "get_source_text",
                        lambda s: "FULL DOCUMENT TEXT" if s == "mtd.pdf" else "")
    def fake_generate(prompt, system=""):
        seen["prompt"] = prompt
        return "Plain-language explanation."
    monkeypatch.setattr(ollama_client, "generate", fake_generate)
    result = rag.summarize_document("mtd.pdf")
    assert result == {"summary": "Plain-language explanation.", "found": True}
    assert "FULL DOCUMENT TEXT" in seen["prompt"]
    assert rag.summarize_document("missing.pdf") == {"summary": "", "found": False}
