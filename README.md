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

## Model

Default generation model is `hf.co/unsloth/gemma-4-E2B-it-GGUF:latest` (fast).
On a faster machine, set `GEN_MODEL = "gemma4:latest"` in `config.py` for better
answers. The first question after startup is slower while the model loads into memory.
