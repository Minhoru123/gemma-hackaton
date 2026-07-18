OLLAMA_URL = "http://localhost:11434"
GEN_MODEL = "gemma4:latest"
EMBED_MODEL = "nomic-embed-text"
DB_PATH = "data/case_companion.db"
TOP_K = 4                 # retrieved chunks per query
MIN_SCORE = 0.55          # below this, answer "I don't know". Tuned: relevant Qs score
                          # 0.62-0.84, off-topic 0.36-0.46, so 0.55 sits in the gap.
CHUNK_CHARS = 900         # target chunk size in characters
CHUNK_OVERLAP = 150

DEADLINE_RULES = "deadline_rules.json"    # presumptive-deadline rules table
DEADLINE_RULES_PROPOSED = "deadline_rules_proposed.json"  # staging, pre-approval
INTAKE_DIR = "intake"                     # drop filings here for processing
INTAKE_DONE_DIR = "intake/completed"      # processed files move here
FETCH_LIST = "data/FETCH_LIST.md"         # citations we still need to capture
MIN_QUOTE_CHARS = 15      # quotes shorter than this are not checked verbatim
