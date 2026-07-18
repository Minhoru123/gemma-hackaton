# Case Companion

On-device legal assistant (Gemma 4 via Ollama). Explains legal documents in plain
English with citations. Runs fully offline.

## Run

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    python scripts/build_corpus.py
    python -m uvicorn app.main:app --port 8000

Open http://localhost:8000

## Models

The app uses two local Ollama models, both fully offline:

- **Generation:** `hf.co/unsloth/gemma-4-E2B-it-GGUF:latest` (fast, default)
- **Embeddings:** `nomic-embed-text`

The first question after startup is slower while the model loads into memory. Ask one
warm-up question before a demo so the model is hot.

## Switching to the bigger model

The default E2B model is fast and good enough for most machines. On a faster machine,
`gemma4:latest` gives noticeably better answers (but is slower: ~100s per answer on a
laptop without a strong GPU, vs ~a few seconds for E2B).

To switch:

1. Make sure the model is pulled:

       ollama pull gemma4:latest

2. In `config.py`, comment out the E2B line and uncomment the gemma4 line:

       # GEN_MODEL = "hf.co/unsloth/gemma-4-E2B-it-GGUF:latest"
       GEN_MODEL = "gemma4:latest"

3. Restart the server. No other code changes are needed — both models work with the
   same `think=False` setting the app already sends.

To switch back, reverse the two comment markers. Only one `GEN_MODEL` line should be
active at a time.

**Tip:** decide which model to demo on based on the machine's speed. If answers take more
than a few seconds, stay on E2B.
