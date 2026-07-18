import os
import datetime
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from app import (cases, store, timeline, ingest, extract, rag, ollama_client,
                 authorities, questions, obligations, deadlines, case_events,
                 advice, jurisdiction, dates, party, rebuild)

app = FastAPI(title="Case Companion")
app.mount("/web", StaticFiles(directory="web"), name="web")
UPLOAD_DIR = "uploads"


@app.on_event("startup")
def _startup():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    cases.init()          # must run first: other stores scope by the active case
    store.init_db()
    jurisdiction.migrate_legacy()  # global jurisdiction key -> per-case
    timeline.init()
    authorities.init_db()
    questions.init()
    obligations.init()
    ollama_client.warmup()


_find_date = dates.find_date  # full-date finder: textual, numeric, and ISO forms


class AskBody(BaseModel):
    question: str
    language: str = "English"


class AdviceBody(BaseModel):
    text: str


class QuestionBody(BaseModel):
    question: str


class CaseCreateBody(BaseModel):
    name: str = ""


class CaseSwitchBody(BaseModel):
    id: int


class CaseRenameBody(BaseModel):
    id: int
    name: str


class CaseDeleteBody(BaseModel):
    id: int


class DocRemoveBody(BaseModel):
    source: str


class DocSummarizeBody(BaseModel):
    source: str
    language: str = "English"


class IdBody(BaseModel):
    id: int


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    path = os.path.join(UPLOAD_DIR, file.filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    text = ingest.extract_text(path)
    chunks = ingest.chunk_text(text)
    store.add_chunks(file.filename, chunks, kind="upload")
    now = datetime.datetime.now().isoformat(timespec="minutes")
    facts = extract.key_facts(text)

    analysis = case_events.analyze(text)
    # Date fallback order: the analyzer's pick (told to prefer the signature/
    # DATED line), then the first date near the signature block at the bottom,
    # then the first date anywhere, then upload day.
    filed = (analysis["filed_date"] or _find_date(text[-3000:])
             or _find_date(text) or now[:10])
    src = file.filename
    timeline.add_event(
        "filed", f"Filed: {src} ({analysis['doc_type']})", filed, source=src)
    for ev in analysis["events"]:
        timeline.add_event("case_event", ev["event"], ev["date"], source=src)
    if facts.get("deadline") and facts["deadline"] != "Not stated":
        when = _find_date(facts["deadline"], text) or now
        timeline.add_event("case_date", f"Deadline: {facts['deadline']}", when,
                           source=src)

    detected = jurisdiction.detect(text)
    current = jurisdiction.get_case()
    if detected and not current:
        jurisdiction.set_case(detected)
        current = detected
    elif detected and current and detected != current:
        questions.add(
            f"{file.filename} appears to come from "
            f"{jurisdiction.LABELS[detected]}, but earlier filings in this "
            f"case are from {jurisdiction.LABELS[current]}. Ask your attorney "
            "which court your case is in — the answer decides which rules "
            "and deadlines apply.",
            source=file.filename)

    origin = party.origin(analysis["filed_by"])
    created = deadlines.apply(analysis["doc_type"], filed, file.filename,
                              jurisdiction=current,
                              filed_by=analysis["filed_by"])
    satisfied = obligations.try_satisfy(analysis["doc_type"],
                                        filed_by=analysis["filed_by"])
    role = party.get()
    for fault in analysis["faults"]:
        fault_side = party.side_of(fault["who"])
        if role and fault_side and fault_side != role:
            tail = ("This concerns the other side and may matter to your "
                    "case — ask your attorney about it.")
        else:
            tail = "Ask your attorney what happened here."
        questions.add(
            f"This {analysis['doc_type']} says: \"{fault['quote']}\" "
            f"({fault['category']}, regarding {fault['who']}). {tail}",
            source=file.filename, context_quote=fault["quote"])

    return {"key_facts": facts, "chunks_added": len(chunks),
            "doc_type": analysis["doc_type"], "filed_date": filed,
            "events_added": len(analysis["events"]),
            "presumptive_deadlines": created,
            "obligations_satisfied": satisfied,
            "faults_flagged": analysis["faults"],
            "jurisdiction": current,
            "jurisdiction_detected": detected,
            "filed_by": analysis["filed_by"],
            "origin": origin}


@app.post("/api/ask")
async def ask(body: AskBody):
    return rag.answer(body.question, body.language)


class RoleBody(BaseModel):
    role: str


@app.get("/api/case")
async def get_case():
    return {"jurisdiction": jurisdiction.get_case(), "role": party.get()}


@app.post("/api/case/role")
async def set_role(body: RoleBody):
    party.set(body.role)  # invalid values are ignored
    return {"jurisdiction": jurisdiction.get_case(), "role": party.get()}


def _cases_state():
    return {"cases": cases.list_all(), "active_id": cases.active_id()}


@app.get("/api/cases")
async def get_cases():
    return _cases_state()


@app.post("/api/cases")
async def create_case(body: CaseCreateBody):
    cases.create(body.name)
    return _cases_state()


@app.post("/api/cases/switch")
async def switch_case(body: CaseSwitchBody):
    cases.set_active(body.id)  # no-op if id doesn't exist
    return _cases_state()


@app.post("/api/cases/rename")
async def rename_case(body: CaseRenameBody):
    cases.rename(body.id, body.name)  # no-op on blank name / unknown id
    return _cases_state()


@app.post("/api/cases/delete")
async def delete_case(body: CaseDeleteBody):
    """Delete a case and all its scoped data. Scoped rows (uploads, timeline,
    questions, obligations) are cleared first (while still identifiable), then
    the case row. Blocked for the last remaining case or an unknown id (in which
    case nothing is deleted). Shared corpus chunks (case_id IS NULL) are never
    touched."""
    ids = {c["id"] for c in cases.list_all()}
    if body.id not in ids or len(ids) <= 1:
        return _cases_state()  # last-case guard / unknown id: no-op
    store.remove_case(body.id)
    timeline.remove_case(body.id)
    questions.remove_case(body.id)
    obligations.remove_case(body.id)
    cases.delete(body.id)  # removes the case row + reactivates if needed
    return _cases_state()


@app.get("/api/documents")
async def get_documents():
    return {"documents": store.list_sources()}


@app.post("/api/documents/summarize")
async def summarize_document(body: DocSummarizeBody):
    """Whole-document plain-language explanation (bypasses chunk retrieval)."""
    return rag.summarize_document(body.source, body.language)


@app.post("/api/documents/remove")
async def remove_document(body: DocRemoveBody):
    """Remove one uploaded document from the active case: its RAG chunks, its
    timeline events, and any system-generated questions from it."""
    removed = store.remove_source(body.source)
    timeline.remove_by_source(body.source)
    questions.remove_by_source(body.source)
    return {"removed_chunks": removed, "documents": store.list_sources()}


@app.get("/api/timeline")
async def get_timeline():
    return {"events": timeline.list_events()}


@app.post("/api/timeline/rebuild")
async def rebuild_timeline():
    """Re-derive the whole timeline from every stored document in the active
    case (slow: re-runs analysis per document)."""
    stats = rebuild.rebuild_timeline()
    return {**stats, "events": timeline.list_events()}


@app.post("/api/check-advice")
async def check_advice(body: AdviceBody):
    return advice.check(body.text)


@app.get("/api/questions")
async def get_questions():
    return {"questions": questions.list_open()}


@app.post("/api/questions/add")
async def add_question(body: QuestionBody):
    questions.add(body.question, source="user")
    return {"questions": questions.list_open()}


@app.post("/api/questions/resolve")
async def resolve_question(body: IdBody):
    questions.resolve(body.id)
    return {"questions": questions.list_open()}


class SuggestBody(BaseModel):
    id: int
    language: str = "English"


@app.get("/api/warnings")
async def get_warnings(view: str = ""):
    """Open obligations; with ?view=plaintiff|defendant, only that side's."""
    if view not in ("plaintiff", "defendant"):
        view = ""
    return {"warnings": obligations.warnings(view=view), "view": view}


@app.post("/api/suggest-arguments")
async def suggest_arguments(body: SuggestBody):
    """Grounded argument ideas for one open obligation's responsive filing."""
    ob = obligations.get(body.id)
    if not ob:
        return {"found": False, "suggestions": ""}
    return rag.suggest_arguments(ob, body.language)


@app.post("/api/obligations/satisfy")
async def satisfy_obligation(body: IdBody):
    obligations.satisfy(body.id)
    return {"warnings": obligations.warnings()}


@app.get("/")
async def index():
    return FileResponse("web/index.html")
