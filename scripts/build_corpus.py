import os
import sys
sys.path.insert(0, os.path.abspath("."))
from app import store, ingest

store.init_db()
folder = "corpus"
for name in os.listdir(folder):
    path = os.path.join(folder, name)
    text = ingest.extract_text(path)
    chunks = ingest.chunk_text(text)
    store.add_chunks(name, chunks, kind="corpus")
    print(f"loaded {name}: {len(chunks)} chunks")
print("corpus built.")
