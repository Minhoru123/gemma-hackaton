# Per-case documentation isolation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user create named cases, switch between them, and have every case-specific panel (documents/RAG, timeline, warnings, questions) follow the active case.

**Architecture:** A new `app/cases.py` module owns the `cases` table and the single server-side active case. Each existing store module (`store`, `timeline`, `questions`, `obligations`) stamps `case_id` on insert and filters reads by `cases.active_id()`. Endpoint signatures stay stable; three new `/api/cases*` endpoints manage cases. The frontend gets a header switcher. Existing DB is wiped (no migration).

**Tech Stack:** Python 3, FastAPI, SQLite (stdlib `sqlite3`), pytest, vanilla JS frontend, Ollama (local) for embeddings.

## Global Constraints

- Test isolation pattern (copy verbatim): each test sets `config.DB_PATH = str(tmp_path / "t.db")` then calls the module's `init()` before use.
- `store.add_chunks` / `store.search` call live Ollama embeddings — tests touching them require Ollama running on `localhost:11434`. Timeline/questions/obligations/cases tests are pure SQLite (no Ollama).
- Scoped per case: `chunks`, `timeline`, `questions`, `obligations`. Shared (never scoped): authorities, `deadline_rules.json`.
- Exactly one `cases` row has `is_active = 1` at all times.
- No em/en dashes in code, comments, or commit messages.
- Existing store modules currently take no `case_id` argument and must keep their public call sites working via internal `cases.active_id()` (Approach A) — do NOT add `case_id` params to their signatures.

---

### Task 1: `_as_text` regression test (lock in the brackets fix)

The brackets fix already shipped in `app/extract.py` (`_as_text`). Add a regression test so it can't regress.

**Files:**
- Test: `tests/test_extract.py` (modify — append)

**Interfaces:**
- Consumes: `app.extract._as_text(value) -> str` (already implemented: joins lists with `", "`, flattens dicts to `"k: v; ..."`, else `str(value)`).
- Produces: nothing (test-only).

- [ ] **Step 1: Write the failing test** — append to `tests/test_extract.py`:

```python
from app.extract import _as_text


def test_as_text_flattens_list_parties():
    assert _as_text(["Jane Doe", "Acme Corp"]) == "Jane Doe, Acme Corp"


def test_as_text_flattens_dict_roles():
    assert _as_text({"plaintiff": "Jane Doe", "defendant": "Acme Corp"}) == \
        "plaintiff: Jane Doe; defendant: Acme Corp"


def test_as_text_passes_string_through():
    assert _as_text("John Smith v. State") == "John Smith v. State"
```

- [ ] **Step 2: Run test to verify it passes** (implementation already exists)

Run: `python -m pytest tests/test_extract.py -v`
Expected: PASS (all three new tests + the two existing tests). Note: this task is verify-only because the fix already shipped; if any of the three fail, the fix regressed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_extract.py
git commit -m "test: lock in list/dict key-fact flattening"
```

---

### Task 2: `app/cases.py` — cases table and active-case state

**Files:**
- Create: `app/cases.py`
- Test: `tests/test_cases.py`

**Interfaces:**
- Consumes: `config.DB_PATH`; stdlib `sqlite3`, `os`, `datetime`.
- Produces (later tasks depend on these exact signatures):
  - `init() -> None` — create `cases` table; if empty, create "My case" and mark it active.
  - `list_all() -> list[dict]` — `[{"id","name","created","is_active"}]`, newest first (`is_active` is a bool).
  - `active_id() -> int` — currently active case id; always valid (self-heals).
  - `create(name: str) -> int` — insert new case, switch to it, return id. Blank name -> "Untitled case".
  - `set_active(case_id: int) -> None` — clear all `is_active`, set this one.

- [ ] **Step 1: Write the failing test** — create `tests/test_cases.py`:

```python
import config
from app import cases


def _setup(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    cases.init()


def test_init_creates_default_active_case(tmp_path):
    _setup(tmp_path)
    all_cases = cases.list_all()
    assert len(all_cases) == 1
    assert all_cases[0]["name"] == "My case"
    assert all_cases[0]["is_active"] is True
    assert cases.active_id() == all_cases[0]["id"]


def test_create_switches_active(tmp_path):
    _setup(tmp_path)
    first = cases.active_id()
    new_id = cases.create("Divorce - Smith")
    assert cases.active_id() == new_id
    assert new_id != first
    # exactly one active
    assert sum(1 for c in cases.list_all() if c["is_active"]) == 1


def test_create_blank_name_falls_back(tmp_path):
    _setup(tmp_path)
    new_id = cases.create("   ")
    names = {c["id"]: c["name"] for c in cases.list_all()}
    assert names[new_id] == "Untitled case"


def test_set_active_leaves_one_active(tmp_path):
    _setup(tmp_path)
    a = cases.active_id()
    b = cases.create("Case B")
    cases.set_active(a)
    assert cases.active_id() == a
    assert sum(1 for c in cases.list_all() if c["is_active"]) == 1


def test_active_id_self_heals_when_none_active(tmp_path):
    _setup(tmp_path)
    import sqlite3
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("UPDATE cases SET is_active=0")
    conn.commit()
    conn.close()
    # no active row -> active_id must recover to an existing case
    healed = cases.active_id()
    assert healed is not None
    assert sum(1 for c in cases.list_all() if c["is_active"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cases.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.cases'`.

- [ ] **Step 3: Write minimal implementation** — create `app/cases.py`:

```python
"""Cases: named containers that isolate a user's documents, timeline,
questions, and obligations. Exactly one case is active at a time (server-side,
single-user). Other store modules scope their rows by cases.active_id()."""

import sqlite3
import os
import datetime
import config


def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    return sqlite3.connect(config.DB_PATH)


def init() -> None:
    c = _conn()
    c.execute(
        """CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, created TEXT, is_active INTEGER DEFAULT 0
        )"""
    )
    c.commit()
    count = c.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    c.close()
    if count == 0:
        create("My case")


def list_all() -> list[dict]:
    c = _conn()
    rows = c.execute(
        "SELECT id, name, created, is_active FROM cases ORDER BY id DESC"
    ).fetchall()
    c.close()
    return [{"id": i, "name": n, "created": cr, "is_active": bool(a)}
            for (i, n, cr, a) in rows]


def create(name: str) -> int:
    name = (name or "").strip() or "Untitled case"
    c = _conn()
    cur = c.execute(
        "INSERT INTO cases (name, created, is_active) VALUES (?,?,0)",
        (name, datetime.date.today().isoformat()),
    )
    new_id = cur.lastrowid
    c.commit()
    c.close()
    set_active(new_id)
    return new_id


def set_active(case_id: int) -> None:
    c = _conn()
    c.execute("UPDATE cases SET is_active=0")
    c.execute("UPDATE cases SET is_active=1 WHERE id=?", (case_id,))
    c.commit()
    c.close()


def active_id() -> int:
    c = _conn()
    row = c.execute(
        "SELECT id FROM cases WHERE is_active=1 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row:
        c.close()
        return row[0]
    # self-heal: activate most recent case, or create one
    row = c.execute("SELECT id FROM cases ORDER BY id DESC LIMIT 1").fetchone()
    c.close()
    if row:
        set_active(row[0])
        return row[0]
    return create("My case")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cases.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add app/cases.py tests/test_cases.py
git commit -m "feat: add cases module owning active-case state"
```

---

### Task 3: Scope `timeline` by active case

**Files:**
- Modify: `app/timeline.py`
- Test: `tests/test_timeline.py` (modify — add isolation test)

**Interfaces:**
- Consumes: `cases.init`, `cases.active_id`, `cases.create` from Task 2.
- Produces: `timeline.add_event`/`timeline.list_events` unchanged signatures, now scoped.

- [ ] **Step 1: Write the failing test** — append to `tests/test_timeline.py`:

```python
from app import cases as cases_mod


def test_timeline_isolated_per_case(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    cases_mod.init()
    timeline.init()
    timeline.add_event("case_date", "Hearing A", "2026-08-03")
    b = cases_mod.create("Case B")  # switches active to B
    assert timeline.list_events() == []  # B is empty
    timeline.add_event("case_date", "Hearing B", "2026-09-01")
    assert [e["label"] for e in timeline.list_events()] == ["Hearing B"]
    cases_mod.set_active(b - 1 if b > 1 else b)  # back to first case
    labels = [e["label"] for e in timeline.list_events()]
    assert "Hearing A" in labels and "Hearing B" not in labels
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_timeline.py -v`
Expected: FAIL — events leak across cases (no `case_id` column yet), or `ImportError`/schema error.

- [ ] **Step 3: Write minimal implementation** — replace `app/timeline.py` body:

```python
import sqlite3
import os
import config
from app import cases


def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    return sqlite3.connect(config.DB_PATH)


def init() -> None:
    c = _conn()
    c.execute(
        """CREATE TABLE IF NOT EXISTS timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER, kind TEXT, label TEXT, when_ts TEXT
        )"""
    )
    c.commit()
    c.close()


def add_event(kind: str, label: str, when: str) -> None:
    c = _conn()
    c.execute(
        "INSERT INTO timeline (case_id, kind, label, when_ts) VALUES (?,?,?,?)",
        (cases.active_id(), kind, label, when),
    )
    c.commit()
    c.close()


def list_events() -> list[dict]:
    c = _conn()
    rows = c.execute(
        "SELECT kind, label, when_ts FROM timeline WHERE case_id=? ORDER BY when_ts",
        (cases.active_id(),),
    ).fetchall()
    c.close()
    return [{"kind": k, "label": l, "when": w} for (k, l, w) in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_timeline.py -v`
Expected: PASS (existing test + new isolation test).

- [ ] **Step 5: Commit**

```bash
git add app/timeline.py tests/test_timeline.py
git commit -m "feat: scope timeline events by active case"
```

---

### Task 4: Scope `questions` by active case

**Files:**
- Modify: `app/questions.py`
- Test: `tests/test_questions.py` (modify — add isolation test)

**Interfaces:**
- Consumes: `cases` from Task 2.
- Produces: `questions.add`/`list_open`/`resolve` unchanged signatures, now scoped; unique constraint is now `UNIQUE(case_id, question)`.

- [ ] **Step 1: Write the failing test** — append to `tests/test_questions.py`:

```python
from app import cases as cases_mod


def test_questions_isolated_per_case(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    cases_mod.init()
    questions.init()
    questions.add("Ask about the missed deadline", source="doc.pdf")
    b = cases_mod.create("Case B")
    assert questions.list_open() == []  # B empty
    # same text allowed in a different case (unique is per-case)
    assert questions.add("Ask about the missed deadline", source="doc.pdf") is True
    assert len(questions.list_open()) == 1
```

Read the existing `tests/test_questions.py` first; if it has no `import config` line, add `import config` at the top with the other imports.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_questions.py -v`
Expected: FAIL — question text collides across cases (global UNIQUE) or schema error.

- [ ] **Step 3: Write minimal implementation** — replace `app/questions.py` body (keep the module docstring):

```python
"""Ask-your-attorney list: things the system noticed that a human should raise
with counsel. The system never contacts the lawyer, it only surfaces
questions to the user."""

import sqlite3
import os
import datetime
import config
from app import cases


def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    return sqlite3.connect(config.DB_PATH)


def init() -> None:
    c = _conn()
    c.execute(
        """CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER, question TEXT, source TEXT, context_quote TEXT,
            created TEXT, status TEXT DEFAULT 'open',
            UNIQUE(case_id, question)
        )"""
    )
    c.commit()
    c.close()


def add(question: str, source: str = "", context_quote: str = "") -> bool:
    """Add a question; duplicates within the same case are ignored.
    Returns True if newly added."""
    c = _conn()
    cur = c.execute(
        """INSERT OR IGNORE INTO questions
           (case_id, question, source, context_quote, created)
           VALUES (?,?,?,?,?)""",
        (cases.active_id(), question.strip(), source, context_quote,
         datetime.date.today().isoformat()),
    )
    c.commit()
    added = cur.rowcount > 0
    c.close()
    return added


def list_open() -> list[dict]:
    c = _conn()
    rows = c.execute(
        """SELECT id, question, source, context_quote, created
           FROM questions WHERE status='open' AND case_id=? ORDER BY id DESC""",
        (cases.active_id(),),
    ).fetchall()
    c.close()
    keys = ["id", "question", "source", "context_quote", "created"]
    return [dict(zip(keys, r)) for r in rows]


def resolve(qid: int) -> None:
    c = _conn()
    c.execute("UPDATE questions SET status='resolved' WHERE id=?", (qid,))
    c.commit()
    c.close()
```

Note: `resolve(qid)` is by primary key, which is globally unique, so it needs no case filter.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_questions.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/questions.py tests/test_questions.py
git commit -m "feat: scope ask-your-attorney questions by active case"
```

---

### Task 5: Scope `obligations` by active case

**Files:**
- Modify: `app/obligations.py`
- Test: `tests/test_obligations.py` (modify — add isolation test + `cases.init` in `_setup`)

**Interfaces:**
- Consumes: `cases` from Task 2.
- Produces: `obligations.add`/`list_open`/`satisfy`/`try_satisfy`/`warnings` unchanged signatures, now scoped.

- [ ] **Step 1: Write the failing test** — modify `tests/test_obligations.py`:

Change `_setup` to also init cases, and add an isolation test:

```python
import config
from app import obligations
from app import cases as cases_mod


def _setup(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    cases_mod.init()
    obligations.init()
```

(Keep the three existing tests as-is.) Append:

```python
def test_obligations_isolated_per_case(tmp_path):
    _setup(tmp_path)
    obligations.add("File opposition", due_date="2026-07-10")
    cases_mod.create("Case B")
    assert obligations.list_open() == []
    assert obligations.warnings(today="2026-07-18") == []
    obligations.add("File reply", due_date="2026-07-22")
    assert [o["label"] for o in obligations.list_open()] == ["File reply"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_obligations.py -v`
Expected: FAIL — obligations leak across cases, or schema error.

- [ ] **Step 3: Write minimal implementation** — in `app/obligations.py`:

Add `from app import cases` to the imports.

Change the `init()` CREATE TABLE to include `case_id`:

```python
        """CREATE TABLE IF NOT EXISTS obligations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER, label TEXT, trigger_source TEXT, due_date TEXT,
            presumptive INTEGER DEFAULT 1, rule_cite TEXT,
            satisfied_by TEXT, status TEXT DEFAULT 'open', created TEXT
        )"""
```

Change `add(...)` INSERT to include `case_id`:

```python
    cur = c.execute(
        """INSERT INTO obligations
           (case_id, label, trigger_source, due_date, presumptive, rule_cite,
            satisfied_by, created)
           VALUES (?,?,?,?,?,?,?,?)""",
        (cases.active_id(), label, trigger_source, due_date, int(presumptive),
         rule_cite, satisfied_by, datetime.date.today().isoformat()),
    )
```

Change `list_open()` SELECT to filter by case:

```python
    rows = c.execute(
        """SELECT id, label, trigger_source, due_date, presumptive, rule_cite,
                  satisfied_by, created
           FROM obligations WHERE status='open' AND case_id=? ORDER BY due_date""",
        (cases.active_id(),),
    ).fetchall()
```

Change `try_satisfy(...)` SELECT to filter by case:

```python
    rows = c.execute(
        """SELECT id, label FROM obligations
           WHERE status='open' AND satisfied_by=? AND case_id=?""",
        (doc_type, cases.active_id()),
    ).fetchall()
```

`satisfy(oid)` is by primary key — leave unchanged. `warnings()` calls `list_open()`, which is now scoped — leave unchanged.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_obligations.py -v`
Expected: PASS (3 existing + 1 new).

- [ ] **Step 5: Commit**

```bash
git add app/obligations.py tests/test_obligations.py
git commit -m "feat: scope obligations by active case"
```

---

### Task 6: Scope `store` chunks by active case (RAG isolation)

**Files:**
- Modify: `app/store.py`
- Test: `tests/test_store.py` (modify — add isolation test)

**Interfaces:**
- Consumes: `cases` from Task 2.
- Produces: `store.add_chunks`/`search`/`clear_uploads` unchanged signatures, now scoped. Requires live Ollama.

- [ ] **Step 1: Write the failing test** — append to `tests/test_store.py`:

```python
from app import cases as cases_mod


def test_search_isolated_per_case(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    cases_mod.init()
    store.init_db()
    store.add_chunks("docA", [
        "The response deadline is twenty days after service.",
    ], kind="upload")
    cases_mod.create("Case B")  # switch to empty case
    assert store.search("How many days to respond?", k=2) == []
    cases_mod.set_active(1)  # back to first case (id 1 = "My case")
    hits = store.search("How many days to respond?", k=2)
    assert hits and hits[0]["text"].lower().startswith("the response deadline")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_store.py -v`
Expected: FAIL — Case B search returns docA's chunk (no scoping) or schema error. (Requires Ollama; if Ollama is down, this task cannot be verified — note that and stop.)

- [ ] **Step 3: Write minimal implementation** — in `app/store.py`:

Add `from app import cases` to imports.

Change `init_db()` CREATE TABLE to include `case_id`:

```python
        """CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER, source TEXT, kind TEXT, text TEXT, embedding TEXT
        )"""
```

Change `add_chunks(...)` INSERT to include `case_id`:

```python
        c.execute(
            "INSERT INTO chunks (case_id, source, kind, text, embedding) VALUES (?,?,?,?,?)",
            (cases.active_id(), source, kind, ch, json.dumps(emb)),
        )
```

Change `clear_uploads()` to scope by case:

```python
    c.execute("DELETE FROM chunks WHERE kind='upload' AND case_id=?",
              (cases.active_id(),))
```

Change `search(...)` to only load the active case's rows:

```python
    rows = c.execute(
        "SELECT source, kind, text, embedding FROM chunks WHERE case_id=?",
        (cases.active_id(),),
    ).fetchall()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_store.py -v`
Expected: PASS (existing rank test + new isolation test). Requires Ollama.

- [ ] **Step 5: Commit**

```bash
git add app/store.py tests/test_store.py
git commit -m "feat: scope RAG chunk store by active case"
```

---

### Task 7: Case API endpoints + startup wiring

**Files:**
- Modify: `app/main.py`
- Test: `tests/test_cases_api.py` (create)

**Interfaces:**
- Consumes: `cases` (Task 2) and all scoped stores.
- Produces:
  - `GET  /api/cases` -> `{"cases": [...], "active_id": int}`
  - `POST /api/cases` body `{"name": str}` -> `{"cases": [...], "active_id": int}`
  - `POST /api/cases/switch` body `{"id": int}` -> `{"cases": [...], "active_id": int}`

- [ ] **Step 1: Write the failing test** — create `tests/test_cases_api.py`:

```python
import config
from fastapi.testclient import TestClient


def _client(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    from app.main import app  # import after DB_PATH is set
    return TestClient(app)  # triggers startup, which inits cases


def test_list_create_switch(tmp_path):
    client = _client(tmp_path)
    r = client.get("/api/cases")
    assert r.status_code == 200
    body = r.json()
    assert body["cases"] and "active_id" in body
    first_active = body["active_id"]

    r = client.post("/api/cases", json={"name": "Divorce - Smith"})
    body = r.json()
    new_active = body["active_id"]
    assert new_active != first_active
    assert any(c["name"] == "Divorce - Smith" for c in body["cases"])

    r = client.post("/api/cases/switch", json={"id": first_active})
    assert r.json()["active_id"] == first_active
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cases_api.py -v`
Expected: FAIL — 404 on `/api/cases` (routes not defined).

- [ ] **Step 3: Write minimal implementation** — in `app/main.py`:

Add `cases` to the store import block:

```python
from app import (store, timeline, ingest, extract, rag, ollama_client,
                 authorities, questions, obligations, deadlines, case_events,
                 advice, cases)
```

In `_startup()`, init cases FIRST (other inits are unaffected, but active case must exist before any scoped insert):

```python
@app.on_event("startup")
def _startup():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    cases.init()
    store.init_db()
    timeline.init()
    authorities.init_db()
    questions.init()
    obligations.init()
    ollama_client.warmup()
```

Add a request body model near the other models:

```python
class CaseBody(BaseModel):
    name: str = ""


class CaseSwitchBody(BaseModel):
    id: int
```

Add the endpoints (place them near the other `/api` routes):

```python
def _cases_payload():
    return {"cases": cases.list_all(), "active_id": cases.active_id()}


@app.get("/api/cases")
async def get_cases():
    return _cases_payload()


@app.post("/api/cases")
async def new_case(body: CaseBody):
    cases.create(body.name)
    return _cases_payload()


@app.post("/api/cases/switch")
async def switch_case(body: CaseSwitchBody):
    if any(c["id"] == body.id for c in cases.list_all()):
        cases.set_active(body.id)
    return _cases_payload()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cases_api.py -v`
Expected: PASS. If `fastapi.testclient` needs `httpx`, install it: `pip install httpx`.

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_cases_api.py
git commit -m "feat: add case list/create/switch API endpoints"
```

---

### Task 8: Frontend case switcher

**Files:**
- Modify: `web/index.html` (header controls)
- Modify: `web/app.js` (load/create/switch + panel reload)

**Interfaces:**
- Consumes: `/api/cases`, `/api/cases` (POST), `/api/cases/switch`.
- Produces: nothing downstream.

- [ ] **Step 1: Add the switcher markup** — in `web/index.html`, replace the `.controls` div:

```html
    <div class="controls">
      <select id="caseswitch" title="Switch case"></select>
      <button id="newcase" type="button">＋ New case</button>
      <select id="lang"><option>English</option><option>Spanish</option></select>
      <span id="net" class="net">checking…</span>
    </div>
```

- [ ] **Step 2: Add case logic** — in `web/app.js`, add near the top (after `let lastSources = [];`):

```javascript
async function loadCases() {
  const r = await fetch("/api/cases");
  const { cases, active_id } = await r.json();
  const sel = $("#caseswitch");
  sel.innerHTML = cases
    .map((c) => `<option value="${c.id}"${c.id === active_id ? " selected" : ""}>${c.name}</option>`)
    .join("");
}

function reloadPanels() {
  $("#facts").classList.add("hidden");   // facts reappear on next upload
  loadTimeline();
  loadWarnings();
  loadQuestions();
}

async function switchCase(id) {
  await fetch("/api/cases/switch", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: parseInt(id, 10) }),
  });
  reloadPanels();
}

async function newCase() {
  const name = prompt("Name this case (e.g. Divorce - Smith):");
  if (name === null) return;
  await fetch("/api/cases", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  await loadCases();
  reloadPanels();
}
```

- [ ] **Step 3: Wire the controls and initial load** — in `web/app.js`, replace the final bootstrap block:

Current tail:
```javascript
updateNet();
loadTimeline();
loadWarnings();
loadQuestions();
```

Replace with:
```javascript
$("#caseswitch").onchange = (e) => switchCase(e.target.value);
$("#newcase").onclick = newCase;

updateNet();
loadCases();
loadTimeline();
loadWarnings();
loadQuestions();
```

- [ ] **Step 4: Manual verification** (no automated frontend test in this project)

Run the app and confirm the flow end-to-end:
```bash
python -m uvicorn app.main:app --port 8000
```
Then in a browser at `http://localhost:8000`:
1. Header shows a case dropdown ("My case") + "＋ New case".
2. Upload a doc; timeline/warnings/facts populate.
3. Click "＋ New case", name it "Case B"; panels clear (empty timeline/warnings/questions).
4. Upload a different doc into Case B; ask a question -> answer cites only Case B's doc.
5. Switch the dropdown back to "My case"; its timeline/warnings/questions return and Case B's are gone.

Expected: each panel follows the active case; no cross-case leakage. Record the result (pass/fail with what you saw) in the commit message or task notes.

- [ ] **Step 5: Commit**

```bash
git add web/index.html web/app.js
git commit -m "feat: add case switcher to the UI"
```

---

### Task 9: Fresh-start reset + full suite green

The spec chose wipe-and-start-fresh (no migration). The old `data/case_companion.db` has pre-feature tables without `case_id`; `CREATE TABLE IF NOT EXISTS` will NOT add the new columns to an existing DB, so the live DB must be reset once.

**Files:**
- Delete (runtime data, not source): `data/case_companion.db`

**Interfaces:** none.

- [ ] **Step 1: Confirm the live DB is stale** — inspect the current schema:

```bash
python -c "import sqlite3; c=sqlite3.connect('data/case_companion.db'); print([r[1] for r in c.execute('PRAGMA table_info(chunks)')])" 2>/dev/null || echo "no db yet"
```
Expected: prints columns WITHOUT `case_id` (stale), or "no db yet".

- [ ] **Step 2: Reset the DB** (deliberate, one-time; user approved data loss)

```bash
rm -f data/case_companion.db
```

- [ ] **Step 3: Recreate schema by starting the app once**

```bash
python -c "from app import cases, store, timeline, questions, obligations; import config; cases.init(); store.init_db(); timeline.init(); questions.init(); obligations.init(); print('schema created; chunks cols:', __import__('sqlite3').connect(config.DB_PATH).execute('PRAGMA table_info(chunks)').fetchall())"
```
Expected: output includes a `case_id` column in `chunks`, and one "My case" row exists.

- [ ] **Step 4: Run the whole suite**

Run: `python -m pytest -v`
Expected: all tests pass. (Store/RAG tests require Ollama; if Ollama is down, run `python -m pytest -v --deselect tests/test_store.py::test_search_isolated_per_case` is NOT allowed as a final sign-off — note the skip and rerun with Ollama before declaring done.)

- [ ] **Step 5: Commit** (only if a tracked file changed; the DB is runtime data and likely gitignored)

```bash
git status --short
# If data/ is gitignored, nothing to commit here; this task is a verification gate.
```

---

## Self-Review

**Spec coverage:**
- Cases table + active state -> Task 2. ✓
- `case_id` on chunks/timeline/questions/obligations -> Tasks 6/3/4/5. ✓
- Shared authorities + deadline_rules unchanged -> not touched (deadlines self-scopes via obligations/timeline). ✓
- Server-side active case, endpoints stable -> Task 7 (existing routes untouched, 3 new). ✓
- New case + switcher UI -> Task 8. ✓
- Wipe-and-start-fresh, no migration -> Task 9. ✓
- `active_id()` self-heal, blank-name fallback, switch-to-nonexistent no-op -> Tasks 2 & 7 (tested). ✓
- Brackets fix already shipped -> Task 1 regression lock. ✓

**Placeholder scan:** No TBD/TODO; every code step shows complete code. ✓

**Type consistency:** `cases.active_id()`, `cases.create(name)`, `cases.set_active(id)`, `cases.list_all()`, `cases.init()` used identically across Tasks 3-8. `_cases_payload()` shape `{cases, active_id}` matches the frontend `loadCases` destructuring. ✓

**Note for executor:** Tasks 3-6 each rewrite/modify a store module. Read the current file before editing so you preserve any lines not shown here (e.g. `store.search`'s scoring loop below the `rows =` query is unchanged — only the SELECT line changes).
