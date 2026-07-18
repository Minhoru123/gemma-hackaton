import os
import sys
sys.path.insert(0, os.path.abspath("."))
from app import store, ingest

store.init_db()
folder = "corpus"
loaded = 0
for name in os.listdir(folder):
    path = os.path.join(folder, name)
    # Skip subdirectories and non-text/PDF files so one bad file can't abort the build.
    if os.path.isdir(path) or not name.lower().endswith((".md", ".txt", ".pdf")):
        print(f"skipped {name} (not a supported corpus file)")
        continue
    try:
        text = ingest.extract_text(path)
        chunks = ingest.chunk_text(text)
        store.add_chunks(name, chunks, kind="corpus")
        print(f"loaded {name}: {len(chunks)} chunks")
        loaded += 1
    except Exception as e:
        print(f"ERROR loading {name}: {e} (skipped)")
if loaded == 0:
    print("WARNING: no corpus files loaded — /api/ask will answer 'I don't know'.")
print("corpus built.")
