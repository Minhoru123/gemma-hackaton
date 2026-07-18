# Case Companion Implementation Plan

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking. This is a hackathon build — favor working software over ceremony. Each task ends with a concrete manual verification, not a heavy test suite.

**Goal:** Build an on-device legal assistant that explains an uploaded legal document in plain English with citations, grounded in a bundled corpus, running entirely offline via Ollama + Gemma 4.

**Architecture:** Python (FastAPI) backend serving a single-page web UI from localhost. The backend runs a RAG pipeline: parse document -> chunk -> embed (nomic-embed-text via Ollama) -> store in SQLite -> retrieve top-k -> build grounded prompt -> call Gemma (E2B) -> strip reasoning scaffold -> return answer + cited sources. Nothing crosses a network.

**Tech Stack:** Python 3.11, FastAPI + uvicorn, SQLite (stdlib `sqlite3`), Ollama HTTP API (`localhost:11434`), `pypdf` for PDF text, numpy for cosine similarity, vanilla HTML/CSS/JS front end (no build step).

## Global Constraints

- Python invoked as `python` (not `python3`). Python 3.11.0.
- All AI runs via local Ollama at `http://localhost:11434` — NO cloud calls, ever. Must work with network disabled.
- Generation model is configurable via one setting `GEN_MODEL` in `config.py`. Default `hf.co/unsloth/gemma-4-E2B-it-GGUF:latest`. Swap to `gemma4:latest` for a faster machine.
- Embedding model `EMBED_MODEL = "nomic-embed-text"` (already pulled).
- E2B leaks `<|channel>thought ...` reasoning scaffold — every generation MUST strip it before returning.
- Domain scope: family law + suing-the-state. Every answer view shows a "This is not legal advice" disclaimer.
- No OCR. PDF-with-selectable-text and plain text only.
- No accounts, no servers beyond localhost, no telemetry.

---

### Task 1: Project scaffold + config + Ollama client

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `app/__init__.py`
- Create: `app/ollama_client.py`
- Create: `.gitignore`
- Create: `README.md`

**Interfaces:**
- Produces: `ollama_client.embed(text: str) -> list[float]`, `ollama_client.generate(prompt: str, system: str = "") -> str` (returns answer with reasoning scaffold already stripped), `ollama_client.warmup() -> None`.
- Produces: `config.GEN_MODEL`, `config.EMBED_MODEL`, `config.OLLAMA_URL`.

- [ ] **Step 1: Create `requirements.txt`**

```
fastapi==0.115.0
uvicorn==0.30.6
pypdf==4.3.1
numpy==2.1.1
python-multipart==0.0.9
```

- [ ] **Step 2: Create `config.py`**

```python
OLLAMA_URL = "http://localhost:11434"
GEN_MODEL = "hf.co/unsloth/gemma-4-E2B-it-GGUF:latest"  # swap to "gemma4:latest" on a faster machine
EMBED_MODEL = "nomic-embed-text"
DB_PATH = "data/case_companion.db"
TOP_K = 4                 # retrieved chunks per query
MIN_SCORE = 0.35          # below this, answer "I don't know"
CHUNK_CHARS = 900         # target chunk size in characters
CHUNK_OVERLAP = 150
```

- [ ] **Step 3: Create `app/__init__.py`** (empty file)

- [ ] **Step 4: Create `app/ollama_client.py`**

```python
import json
import re
import urllib.request
import config

_THOUGHT_RE = re.compile(r"<\|channel\|?>thought.*?(?=<\|)", re.DOTALL)
_TAG_RE = re.compile(r"<\|[^>]*\|?>")


def _post(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        config.OLLAMA_URL + path, data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def strip_scaffold(text: str) -> str:
    """Remove E2B reasoning-model channel scaffolding, keep the final answer."""
    text = _THOUGHT_RE.sub("", text)
    text = _TAG_RE.sub("", text)
    # Some builds prefix the final answer with 'final'/'answer' channel words.
    text = re.sub(r"^\s*(final|answer)\s*", "", text, flags=re.IGNORECASE)
    return text.strip()


def embed(text: str) -> list[float]:
    d = _post("/api/embeddings", {"model": config.EMBED_MODEL, "prompt": text})
    return d["embedding"]


def generate(prompt: str, system: str = "") -> str:
    payload = {"model": config.GEN_MODEL, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system
    d = _post("/api/generate", payload)
    return strip_scaffold(d.get("response", ""))


def warmup() -> None:
    try:
        generate("Reply with the single word: ready.")
    except Exception:
        pass
```

- [ ] **Step 5: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
venv/
data/*.db
uploads/
```

- [ ] **Step 6: Create minimal `README.md`**

```markdown
# Case Companion

On-device legal assistant (Gemma 4 via Ollama). Explains legal documents in plain
English with citations. Runs fully offline.

## Run
    python -m venv .venv && .venv\Scripts\activate
    pip install -r requirements.txt
    python -m uvicorn app.main:app --port 8000
Open http://localhost:8000
```

- [ ] **Step 7: Install deps and verify the Ollama client**

Run:
```bash
python -m venv .venv && source .venv/Scripts/activate && pip install -r requirements.txt
python -c "from app import ollama_client as o; print('embed dims:', len(o.embed('hi'))); print('gen:', o.generate('Reply with the single word: ready.')[:60])"
```
Expected: prints a dimension count (e.g. `embed dims: 768`) and a short generated reply with no `<|channel|>` tags.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt config.py app/ .gitignore README.md
git commit -m "feat: project scaffold, config, and offline Ollama client"
```

---

### Task 2: Document parsing + chunking

**Files:**
- Create: `app/ingest.py`
- Create: `tests/test_ingest.py`

**Interfaces:**
- Consumes: `config.CHUNK_CHARS`, `config.CHUNK_OVERLAP`.
- Produces: `ingest.extract_text(path: str) -> str`, `ingest.chunk_text(text: str) -> list[str]`.

- [ ] **Step 1: Create `app/ingest.py`**

```python
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
```

- [ ] **Step 2: Create `tests/test_ingest.py`**

```python
from app.ingest import chunk_text


def test_chunk_splits_long_text_with_overlap():
    text = "word " * 1000  # ~5000 chars
    chunks = chunk_text(text)
    assert len(chunks) > 1
    assert all(len(c) <= 900 for c in chunks)


def test_chunk_empty_returns_empty():
    assert chunk_text("   ") == []
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_ingest.py -v` (install pytest first: `pip install pytest`)
Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add app/ingest.py tests/test_ingest.py
git commit -m "feat: PDF/text extraction and character chunking"
```

---

### Task 3: SQLite vector store + retrieval

**Files:**
- Create: `app/store.py`
- Create: `tests/test_store.py`

**Interfaces:**
- Consumes: `ollama_client.embed`, `config.DB_PATH`, `config.TOP_K`.
- Produces: `store.init_db() -> None`; `store.add_chunks(source: str, chunks: list[str], kind: str) -> None` (kind is `"corpus"` or `"upload"`); `store.search(query: str, k: int = TOP_K) -> list[dict]` where each dict is `{"text": str, "source": str, "kind": str, "score": float}`; `store.clear_uploads() -> None`.

- [ ] **Step 1: Create `app/store.py`**

```python
import sqlite3
import json
import numpy as np
import config
from app import ollama_client


def _conn():
    import os
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    c = sqlite3.connect(config.DB_PATH)
    return c


def init_db() -> None:
    c = _conn()
    c.execute(
        """CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT, kind TEXT, text TEXT, embedding TEXT
        )"""
    )
    c.commit()
    c.close()


def add_chunks(source: str, chunks: list[str], kind: str) -> None:
    c = _conn()
    for ch in chunks:
        emb = ollama_client.embed(ch)
        c.execute(
            "INSERT INTO chunks (source, kind, text, embedding) VALUES (?,?,?,?)",
            (source, kind, ch, json.dumps(emb)),
        )
    c.commit()
    c.close()


def clear_uploads() -> None:
    c = _conn()
    c.execute("DELETE FROM chunks WHERE kind='upload'")
    c.commit()
    c.close()


def search(query: str, k: int = config.TOP_K) -> list[dict]:
    q = np.array(ollama_client.embed(query), dtype=np.float32)
    qn = q / (np.linalg.norm(q) + 1e-9)
    c = _conn()
    rows = c.execute("SELECT source, kind, text, embedding FROM chunks").fetchall()
    c.close()
    scored = []
    for source, kind, text, emb_json in rows:
        v = np.array(json.loads(emb_json), dtype=np.float32)
        vn = v / (np.linalg.norm(v) + 1e-9)
        score = float(np.dot(qn, vn))
        scored.append({"text": text, "source": source, "kind": kind, "score": score})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:k]
```

- [ ] **Step 2: Create `tests/test_store.py`** (integration — needs Ollama running)

```python
import config
from app import store


def test_add_and_search_ranks_relevant_chunk_first(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    store.init_db()
    store.add_chunks("doc", [
        "The response deadline is twenty days after service.",
        "The cafeteria serves lunch at noon on weekdays.",
    ], kind="corpus")
    results = store.search("How many days do I have to respond?", k=2)
    assert results[0]["text"].lower().startswith("the response deadline")
    assert results[0]["score"] > results[1]["score"]
```

- [ ] **Step 3: Run test**

Run: `python -m pytest tests/test_store.py -v`
Expected: 1 passed (retrieval ranks the deadline chunk first).

- [ ] **Step 4: Commit**

```bash
git add app/store.py tests/test_store.py
git commit -m "feat: SQLite embedding store with cosine retrieval"
```

---

### Task 4: RAG answer engine (grounded prompt + citations + I-don't-know guardrail)

**Files:**
- Create: `app/rag.py`
- Create: `tests/test_rag.py`

**Interfaces:**
- Consumes: `store.search`, `ollama_client.generate`, `config.MIN_SCORE`.
- Produces: `rag.answer(question: str, language: str = "English") -> dict` returning `{"answer": str, "sources": list[dict], "grounded": bool}`. Each source dict is `{"source": str, "kind": str, "text": str, "score": float}`. When top score < MIN_SCORE, `grounded=False` and answer is the "I don't have information" message.

- [ ] **Step 1: Create `app/rag.py`**

```python
import config
from app import store, ollama_client

DISCLAIMER = "This is general information, not legal advice."

SYSTEM = (
    "You are Case Companion, a calm assistant that explains legal documents to people "
    "handling family-law or suing-the-state cases. Use plain, reassuring language. "
    "Answer ONLY from the provided context. If the context does not contain the answer, "
    "say you don't have that information. Never invent legal facts, deadlines, or outcomes."
)

IDK = ("I don't have information about that in your documents. "
       "Please check with your lawyer or the court.")


def _build_prompt(question: str, chunks: list[dict], language: str) -> str:
    ctx = "\n\n".join(f"[Source {i+1}: {c['source']}]\n{c['text']}"
                      for i, c in enumerate(chunks))
    return (
        f"Context:\n{ctx}\n\n"
        f"Question: {question}\n\n"
        f"Answer in {language}, in plain language, citing sources like [Source 1] "
        f"when you use them. If the context lacks the answer, say you don't have it."
    )


def answer(question: str, language: str = "English") -> dict:
    hits = store.search(question)
    grounded = bool(hits) and hits[0]["score"] >= config.MIN_SCORE
    if not grounded:
        return {"answer": IDK, "sources": [], "grounded": False}
    prompt = _build_prompt(question, hits, language)
    text = ollama_client.generate(prompt, system=SYSTEM)
    return {"answer": text, "sources": hits, "grounded": True}
```

- [ ] **Step 2: Create `tests/test_rag.py`**

```python
import config
from app import store, rag


def test_low_relevance_triggers_i_dont_know(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    config.MIN_SCORE = 0.99  # force the guardrail
    store.init_db()
    store.add_chunks("doc", ["Unrelated content about gardening."], kind="corpus")
    result = rag.answer("What is my court deadline?")
    assert result["grounded"] is False
    assert "don't have information" in result["answer"]
```

- [ ] **Step 3: Run test**

Run: `python -m pytest tests/test_rag.py -v`
Expected: 1 passed (guardrail fires).

- [ ] **Step 4: Commit**

```bash
git add app/rag.py tests/test_rag.py
git commit -m "feat: RAG answer engine with citations and I-don't-know guardrail"
```

---

### Task 5: Key-facts + risk extraction

**Files:**
- Create: `app/extract.py`
- Create: `tests/test_extract.py`

**Interfaces:**
- Consumes: `ollama_client.generate`.
- Produces: `extract.key_facts(document_text: str) -> dict` returning `{"summary": str, "parties": str, "deadline": str, "amount": str, "action_required": str, "risks": list[str]}`. Missing fields are the string `"Not stated"` (or empty list for risks). Robust to model returning extra prose around the JSON.

- [ ] **Step 1: Create `app/extract.py`**

```python
import json
import re
from app import ollama_client

_PROMPT = (
    "Extract key facts from this legal document. Return ONLY a JSON object with keys: "
    "summary (one sentence), parties, deadline, amount, action_required, "
    "risks (array of short plain-English risk warnings, e.g. missed-deadline consequences). "
    "Use \"Not stated\" for anything not present. Document:\n\n{doc}"
)

_FIELDS = ["summary", "parties", "deadline", "amount", "action_required"]


def _extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def key_facts(document_text: str) -> dict:
    raw = ollama_client.generate(_PROMPT.format(doc=document_text[:4000]))
    data = _extract_json(raw)
    out = {f: str(data.get(f, "Not stated")) or "Not stated" for f in _FIELDS}
    risks = data.get("risks", [])
    out["risks"] = [str(r) for r in risks] if isinstance(risks, list) else []
    return out
```

- [ ] **Step 2: Create `tests/test_extract.py`**

```python
from app.extract import _extract_json


def test_extract_json_from_surrounding_prose():
    text = 'Here you go: {"summary": "A divorce hearing notice.", "risks": ["Miss the deadline -> default judgment."]} Done.'
    data = _extract_json(text)
    assert data["summary"].startswith("A divorce")
    assert data["risks"][0].startswith("Miss the deadline")


def test_extract_json_bad_input_returns_empty():
    assert _extract_json("no json here") == {}
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_extract.py -v`
Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add app/extract.py tests/test_extract.py
git commit -m "feat: key-facts and risk extraction from documents"
```

---

### Task 6: Timeline store

**Files:**
- Create: `app/timeline.py`
- Create: `tests/test_timeline.py`

**Interfaces:**
- Consumes: `config.DB_PATH`.
- Produces: `timeline.init() -> None`; `timeline.add_event(kind: str, label: str, when: str) -> None` (kind is `"upload"` or `"case_date"`, `when` is an ISO date/datetime string passed in by the caller — no clock call inside); `timeline.list_events() -> list[dict]` sorted by `when`, each `{"kind": str, "label": str, "when": str}`.

- [ ] **Step 1: Create `app/timeline.py`**

```python
import sqlite3
import config


def _conn():
    import os
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    return sqlite3.connect(config.DB_PATH)


def init() -> None:
    c = _conn()
    c.execute(
        """CREATE TABLE IF NOT EXISTS timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT, label TEXT, when_ts TEXT
        )"""
    )
    c.commit()
    c.close()


def add_event(kind: str, label: str, when: str) -> None:
    c = _conn()
    c.execute("INSERT INTO timeline (kind, label, when_ts) VALUES (?,?,?)",
              (kind, label, when))
    c.commit()
    c.close()


def list_events() -> list[dict]:
    c = _conn()
    rows = c.execute(
        "SELECT kind, label, when_ts FROM timeline ORDER BY when_ts"
    ).fetchall()
    c.close()
    return [{"kind": k, "label": l, "when": w} for (k, l, w) in rows]
```

- [ ] **Step 2: Create `tests/test_timeline.py`**

```python
import config
from app import timeline


def test_events_sorted_by_when(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    timeline.init()
    timeline.add_event("case_date", "Hearing", "2026-08-03")
    timeline.add_event("upload", "Uploaded notice", "2026-07-18")
    events = timeline.list_events()
    assert [e["when"] for e in events] == ["2026-07-18", "2026-08-03"]
```

- [ ] **Step 3: Run test**

Run: `python -m pytest tests/test_timeline.py -v`
Expected: 1 passed.

- [ ] **Step 4: Commit**

```bash
git add app/timeline.py tests/test_timeline.py
git commit -m "feat: timeline event store"
```

---

### Task 7: FastAPI backend wiring all endpoints

**Files:**
- Create: `app/main.py`
- Create: `data/.gitkeep`

**Interfaces:**
- Consumes: everything above.
- Produces HTTP endpoints:
  - `POST /api/upload` (multipart file) -> `{key_facts: {...}, chunks_added: int}`. Side effects: extracts text, chunks + embeds as kind `upload`, records an `upload` timeline event with a server local-clock timestamp, and adds any extracted `deadline` as a `case_date` timeline event.
  - `POST /api/ask` (`{question, language}`) -> `rag.answer(...)` dict.
  - `GET /api/timeline` -> `{events: [...]}`.
  - `POST /api/draft-lawyer` (`{question, key_fact}`) -> `{subject: str, body: str}` (drafts only; never sends).
  - `GET /` -> serves `web/index.html`.
  - Startup: `store.init_db()`, `timeline.init()`, `ollama_client.warmup()`.

- [ ] **Step 1: Create `data/.gitkeep`** (empty file so the folder exists)

- [ ] **Step 2: Create `app/main.py`**

```python
import os
import datetime
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel

import config
from app import store, timeline, ingest, extract, rag

app = FastAPI(title="Case Companion")
UPLOAD_DIR = "uploads"


@app.on_event("startup")
def _startup():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    store.init_db()
    timeline.init()
    ollama_warmup()


def ollama_warmup():
    from app import ollama_client
    ollama_client.warmup()


class AskBody(BaseModel):
    question: str
    language: str = "English"


class DraftBody(BaseModel):
    question: str
    key_fact: str = ""


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    path = os.path.join(UPLOAD_DIR, file.filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    text = ingest.extract_text(path)
    chunks = ingest.chunk_text(text)
    store.add_chunks(file.filename, chunks, kind="upload")
    now = datetime.datetime.now().isoformat(timespec="minutes")
    timeline.add_event("upload", f"Uploaded {file.filename}", now)
    facts = extract.key_facts(text)
    if facts.get("deadline") and facts["deadline"] != "Not stated":
        timeline.add_event("case_date", f"Deadline: {facts['deadline']}", facts["deadline"])
    return {"key_facts": facts, "chunks_added": len(chunks)}


@app.post("/api/ask")
async def ask(body: AskBody):
    return rag.answer(body.question, body.language)


@app.get("/api/timeline")
async def get_timeline():
    return {"events": timeline.list_events()}


@app.post("/api/draft-lawyer")
async def draft_lawyer(body: DraftBody):
    subject = "Question about my case"
    body_text = (
        "Hello,\n\nI'm using Case Companion to understand my case and I have a question.\n\n"
        f"Regarding: {body.key_fact or 'my case'}\n"
        f"My question: {body.question}\n\n"
        "Could you please advise? Thank you."
    )
    return {"subject": subject, "body": body_text}


@app.get("/")
async def index():
    return FileResponse("web/index.html")
```

- [ ] **Step 3: Smoke-test the API**

Run:
```bash
python -m uvicorn app.main:app --port 8000 &
sleep 4
curl -s -X POST http://localhost:8000/api/ask -H "Content-Type: application/json" -d '{"question":"hello"}' | head -c 200
```
Expected: JSON with `answer`, `sources`, `grounded` keys (grounded likely false on an empty DB — that is correct).

- [ ] **Step 4: Commit**

```bash
git add app/main.py data/.gitkeep
git commit -m "feat: FastAPI backend wiring upload, ask, timeline, draft endpoints"
```

---

### Task 8: Web UI (single page)

**Files:**
- Create: `web/index.html`
- Create: `web/style.css`
- Create: `web/app.js`

**Interfaces:**
- Consumes: the Task 7 endpoints.
- Produces: a single page with: header + language toggle (English/Spanish) + offline indicator; an upload drop zone; a key-facts card (summary, parties, deadline, amount, action required) with a risks list and a "Ask my lawyer" button; a chat panel showing answers with clickable `[Source N]` citations that reveal the retrieved snippet; a timeline panel; and a persistent "not legal advice" disclaimer footer.

- [ ] **Step 1: Create `web/index.html`**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Case Companion</title>
  <link rel="stylesheet" href="/web/style.css" />
</head>
<body>
  <header>
    <h1>Case Companion</h1>
    <div class="controls">
      <select id="lang"><option>English</option><option>Spanish</option></select>
      <span id="net" class="net">checking…</span>
    </div>
  </header>

  <main>
    <section class="col">
      <div id="drop" class="drop">Drop a PDF or text file, or click to choose</div>
      <input id="file" type="file" accept=".pdf,.txt,.md" hidden />
      <div id="facts" class="card hidden"></div>
      <div id="timeline" class="card"></div>
    </section>

    <section class="col chatcol">
      <div id="chat" class="chat"></div>
      <form id="askform">
        <input id="q" placeholder="Ask a question about your case…" autocomplete="off" />
        <button>Ask</button>
      </form>
    </section>
  </main>

  <footer>This is general information, not legal advice.</footer>
  <script src="/web/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Add static file serving to `app/main.py`**

Add near the top after `app = FastAPI(...)`:
```python
from fastapi.staticfiles import StaticFiles
app.mount("/web", StaticFiles(directory="web"), name="web")
```

- [ ] **Step 3: Create `web/style.css`**

```css
* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, sans-serif; color: #1a1a2e; background: #f4f5fb; }
header { display: flex; justify-content: space-between; align-items: center;
  padding: 12px 20px; background: #2b2d6e; color: #fff; }
header h1 { font-size: 1.1rem; margin: 0; }
.controls { display: flex; gap: 10px; align-items: center; }
.net { font-size: .8rem; padding: 3px 8px; border-radius: 10px; background: #4a4d99; }
.net.off { background: #2e7d32; }
main { display: flex; gap: 16px; padding: 16px; align-items: flex-start; }
.col { flex: 1; display: flex; flex-direction: column; gap: 16px; }
.chatcol { flex: 1.3; }
.card { background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.hidden { display: none; }
.drop { background: #fff; border: 2px dashed #b0b3d6; border-radius: 12px;
  padding: 28px; text-align: center; color: #555; cursor: pointer; }
.facts-row { display: flex; justify-content: space-between; padding: 6px 0;
  border-bottom: 1px solid #eee; font-size: .92rem; }
.risk { background: #fdecea; color: #a12; border-radius: 8px; padding: 8px 10px; margin: 6px 0; font-size: .9rem; }
.chat { background: #fff; border-radius: 12px; padding: 16px; min-height: 320px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08); overflow-y: auto; max-height: 60vh; }
.msg { margin: 10px 0; }
.msg.you { text-align: right; }
.bubble { display: inline-block; padding: 8px 12px; border-radius: 12px; max-width: 85%; }
.you .bubble { background: #2b2d6e; color: #fff; }
.bot .bubble { background: #eef0fb; }
.cite { color: #2b2d6e; cursor: pointer; text-decoration: underline; font-weight: 600; }
.snippet { background: #fffbe6; border-left: 3px solid #d4b106; padding: 8px;
  margin: 6px 0; font-size: .85rem; }
#askform { display: flex; gap: 8px; margin-top: 10px; }
#q { flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 8px; }
button { padding: 10px 16px; background: #2b2d6e; color: #fff; border: none;
  border-radius: 8px; cursor: pointer; }
footer { text-align: center; padding: 12px; color: #777; font-size: .82rem; }
.tl-item { display: flex; gap: 8px; padding: 5px 0; font-size: .9rem; }
.tl-when { color: #2b2d6e; font-weight: 600; min-width: 96px; }
```

- [ ] **Step 4: Create `web/app.js`**

```javascript
const $ = (s) => document.querySelector(s);
const chat = $("#chat");
let lastSources = [];

function bubble(text, who) {
  const d = document.createElement("div");
  d.className = "msg " + who;
  d.innerHTML = `<span class="bubble">${text}</span>`;
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
  return d;
}

function linkCitations(text) {
  return text.replace(/\[Source (\d+)\]/g,
    (m, n) => `<span class="cite" data-i="${n}">${m}</span>`);
}

// Upload
$("#drop").onclick = () => $("#file").click();
$("#file").onchange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  $("#drop").textContent = "Reading " + file.name + "…";
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch("/api/upload", { method: "POST", body: fd });
  const data = await r.json();
  renderFacts(data.key_facts);
  $("#drop").textContent = "Uploaded " + file.name + " — drop another to add";
  loadTimeline();
};

function renderFacts(f) {
  const card = $("#facts");
  card.classList.remove("hidden");
  const rows = [
    ["Summary", f.summary], ["Parties", f.parties],
    ["Deadline", f.deadline], ["Amount", f.amount],
    ["Action required", f.action_required],
  ].map(([k, v]) => `<div class="facts-row"><b>${k}</b><span>${v}</span></div>`).join("");
  const risks = (f.risks || []).map((r) => `<div class="risk">⚠️ ${r}</div>`).join("");
  card.innerHTML = `<h3>Key facts</h3>${rows}${risks}
    <button id="asklawyer">✉️ Ask my lawyer about this</button>`;
  $("#asklawyer").onclick = () => draftLawyer(f.deadline);
}

async function draftLawyer(keyFact) {
  const q = prompt("What do you want to ask your lawyer?");
  if (!q) return;
  const r = await fetch("/api/draft-lawyer", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: q, key_fact: keyFact }),
  });
  const d = await r.json();
  window.location.href =
    `mailto:?subject=${encodeURIComponent(d.subject)}&body=${encodeURIComponent(d.body)}`;
}

// Ask
$("#askform").onsubmit = async (e) => {
  e.preventDefault();
  const q = $("#q").value.trim();
  if (!q) return;
  bubble(q, "you");
  $("#q").value = "";
  const thinking = bubble("…", "bot");
  const r = await fetch("/api/ask", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: q, language: $("#lang").value }),
  });
  const data = await r.json();
  lastSources = data.sources || [];
  thinking.querySelector(".bubble").innerHTML = linkCitations(data.answer);
};

// Citation click reveals snippet
chat.onclick = (e) => {
  if (!e.target.classList.contains("cite")) return;
  const i = parseInt(e.target.dataset.i, 10) - 1;
  const src = lastSources[i];
  if (!src) return;
  const s = document.createElement("div");
  s.className = "snippet";
  s.textContent = `${src.source}: ${src.text}`;
  e.target.closest(".msg").appendChild(s);
};

// Timeline
async function loadTimeline() {
  const r = await fetch("/api/timeline");
  const { events } = await r.json();
  $("#timeline").innerHTML = "<h3>Case timeline</h3>" + (events.length
    ? events.map((e) =>
        `<div class="tl-item"><span class="tl-when">${e.when}</span><span>${e.label}</span></div>`).join("")
    : "<p>No events yet. Upload a document to begin.</p>");
}

// Offline indicator
function updateNet() {
  const el = $("#net");
  if (navigator.onLine) { el.textContent = "🌐 Online"; el.classList.remove("off"); }
  else { el.textContent = "🔒 Offline — still working"; el.classList.add("off"); }
}
window.addEventListener("online", updateNet);
window.addEventListener("offline", updateNet);
updateNet();
loadTimeline();
```

- [ ] **Step 5: Manual end-to-end verification**

Run: `python -m uvicorn app.main:app --port 8000`, open `http://localhost:8000`.
Verify: upload a sample legal `.txt` -> key-facts card fills in and a risk shows -> ask "How many days to respond?" -> answer appears with a clickable `[Source 1]` that reveals the snippet -> timeline shows the upload. Then disable WiFi and ask another question -> it still answers.

- [ ] **Step 6: Commit**

```bash
git add web/ app/main.py
git commit -m "feat: single-page web UI with citations, key-facts, timeline, offline indicator"
```

---

### Task 9: Seed corpus + sample demo document

**Files:**
- Create: `corpus/family_law_rights.md`
- Create: `corpus/suing_state_rights.md`
- Create: `samples/notice_of_hearing.txt`
- Create: `scripts/build_corpus.py`

**Interfaces:**
- Consumes: `ingest`, `store`.
- Produces: `scripts/build_corpus.py` that loads every file in `corpus/` into the SQLite store as kind `corpus`. Run once to build the shareable bundle.

- [ ] **Step 1: Create `corpus/family_law_rights.md`** — a plain-English reference (respondent deadlines, what a dissolution petition is, default judgment, right to respond, where to get legal aid). ~30-40 short factual sentences.

- [ ] **Step 2: Create `corpus/suing_state_rights.md`** — plain-English reference on suing a government entity (notice-of-claim requirement, short deadlines, sovereign immunity basics, where to file). ~30-40 sentences.

- [ ] **Step 3: Create `samples/notice_of_hearing.txt`** — the demo document:

```
NOTICE OF HEARING
Case No. FL-2026-0142
IN RE: The Marriage of Jordan Rivera (Petitioner) and Alex Rivera (Respondent)

A hearing on the Petition for Dissolution of Marriage is scheduled for August 3, 2026
at 9:00 AM in Department 4. The Respondent must file a written Response to the Petition
within 20 days of service of this notice. If the Respondent fails to file a timely
Response, the court may enter a default judgment granting the relief requested in the
Petition, including orders regarding property division and child custody.
```

- [ ] **Step 4: Create `scripts/build_corpus.py`**

```python
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
```

- [ ] **Step 5: Build the corpus and verify retrieval**

Run:
```bash
python scripts/build_corpus.py
python -c "from app import rag; import json; print(json.dumps(rag.answer('How many days do I have to respond to a dissolution petition?'), indent=2, default=str)[:600])"
```
Expected: a grounded answer citing a corpus source about the 20-day / response deadline.

- [ ] **Step 6: Commit**

```bash
git add corpus/ samples/ scripts/build_corpus.py
git commit -m "feat: seed rights corpus, demo document, and corpus builder"
```

---

### Task 10: Demo polish + offline verification

**Files:**
- Modify: `README.md`
- Create: `DEMO.md`

- [ ] **Step 1: Write `DEMO.md`** — the exact 3-minute script: (1) open app, (2) upload `samples/notice_of_hearing.txt`, (3) point at key-facts card + risk flag, (4) ask "What happens if I miss the deadline?" -> cited answer, (5) click a citation to show the source, (6) toggle language to Spanish and re-ask, (7) **disable WiFi and ask a final question** to prove on-device, (8) mention the shareable-bundle vision. Include the one-line data-provenance answer ("public-record case data, retrievable by case number").

- [ ] **Step 2: Warm-up + model note in README** — document swapping `GEN_MODEL` to `gemma4:latest` on a faster machine, and that the first question after start is slower (model load).

- [ ] **Step 3: Full offline dry-run**

Run the app, build corpus, then **turn off WiFi** and execute the entire DEMO.md sequence end to end. Confirm every step works with no network.
Expected: upload, key-facts, cited Q&A, Spanish, and timeline all function offline.

- [ ] **Step 4: Commit**

```bash
git add README.md DEMO.md
git commit -m "docs: demo script and offline verification notes"
```

---

## Self-Review

**Spec coverage:**
- Core upload -> cited RAG Q&A -> network-off: Tasks 2,3,4,7,8,10 ✅
- #1 clickable citations: Task 8 (citation click reveals snippet) ✅
- #2 I-don't-know guardrail: Task 4 (MIN_SCORE) ✅
- #3 key-facts card: Tasks 5,8 ✅
- #3a draft-to-lawyer (drafts only): Tasks 7,8 (mailto, never sends) ✅
- #4 network-off choreography: Task 10 DEMO.md ✅
- #7 Spanish: Tasks 4,8 (language param + toggle) ✅
- #8 risk flags: Tasks 5,8 ✅
- #9 timeline: Tasks 6,7,8 ✅
- Disclaimer: Task 8 footer ✅
- On-device / no cloud: embeddings + generation both via local Ollama ✅
- PDF-with-text + plain text, no OCR: Task 2 ✅
- Model configurable, E2B scaffold stripping: Tasks 1 (config + strip_scaffold) ✅

**Type consistency:** `store.search` returns dicts with `text/source/kind/score`, consumed identically in `rag.answer` and surfaced to the UI as `sources`. `key_facts` returns the field set the UI renders. Timeline events use `kind/label/when` end to end. Consistent ✅

**Build-risk list (tracked during execution):**
1. E2B scaffold-stripping regex may not catch every channel variant — verify actual output early (Task 1 Step 7) and widen the regex if tags leak.
2. gemma4:latest ~100s/answer on this machine — keep E2B default; only switch on a faster machine.
3. First-call latency (model load) — `warmup()` on startup mitigates.
4. PDF text extraction quality varies — demo document is plain `.txt` to remove that risk from the critical path.
5. Spanish quality on E2B unverified — test before relying on it live; English is the fallback.
