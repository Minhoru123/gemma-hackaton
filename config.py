OLLAMA_URL = "http://localhost:11434"
GEN_MODEL = "hf.co/unsloth/gemma-4-E2B-it-GGUF:latest"  # swap to "gemma4:latest" on a faster machine
EMBED_MODEL = "nomic-embed-text"
DB_PATH = "data/case_companion.db"
TOP_K = 4                 # retrieved chunks per query
MIN_SCORE = 0.55          # below this, answer "I don't know". Tuned: relevant Qs score
                          # 0.62-0.84, off-topic 0.36-0.46, so 0.55 sits in the gap.
CHUNK_CHARS = 900         # target chunk size in characters
CHUNK_OVERLAP = 150
