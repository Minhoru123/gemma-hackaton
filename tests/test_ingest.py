from app.ingest import chunk_text


def test_chunk_splits_long_text_with_overlap():
    text = "word " * 1000  # ~5000 chars
    chunks = chunk_text(text)
    assert len(chunks) > 1
    assert all(len(c) <= 900 for c in chunks)


def test_chunk_empty_returns_empty():
    assert chunk_text("   ") == []
