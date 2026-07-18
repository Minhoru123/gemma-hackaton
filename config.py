OLLAMA_URL = "http://localhost:11434"

# --- Generation model -------------------------------------------------------
# To use the bigger, higher-quality model on a faster machine, comment out the
# E2B line and uncomment the gemma4 line below. See README ("Switching models").
GEN_MODEL = "hf.co/unsloth/gemma-4-E2B-it-GGUF:latest"  # fast, default (needs think=False)
# GEN_MODEL = "gemma4:latest"                           # slower, better answers
# ----------------------------------------------------------------------------

EMBED_MODEL = "nomic-embed-text"
DB_PATH = "data/case_companion.db"
TOP_K = 4                 # retrieved chunks per query
MIN_SCORE = 0.55          # below this, answer "I don't know". Tuned: relevant Qs score
                          # 0.62-0.84, off-topic 0.36-0.46, so 0.55 sits in the gap.
CHUNK_CHARS = 900         # target chunk size in characters
CHUNK_OVERLAP = 150
