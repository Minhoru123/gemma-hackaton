import os
import re
import datetime
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from app import (store, timeline, ingest, extract, rag, ollama_client,
                 authorities, questions, obligations, deadlines, case_events,
                 advice)

app = FastAPI(title="Case Companion")
app.mount("/web", StaticFiles(directory="web"), name="web")
UPLOAD_DIR = "uploads"


@app.on_event("startup")
def _startup():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    store.init_db()
    timeline.init()
    authorities.init_db()
    questions.init()
    obligations.init()
    ollama_client.warmup()


_MONTHS = ("January|February|March|April|May|June|July|August|September|"
           "October|November|December")
_DATE_RE = re.compile(rf"((?:{_MONTHS})\s+\d{{1,2}},\s+\d{{4}})")


def _find_date(*texts: str) -> str:
    """Return the first 'Month D, YYYY' date found, as an ISO date for sorting,
    or '' if none. Falls back gracefully if the date can't be parsed."""
    for t in texts:
        m = _DATE_RE.search(t or "")
        if m:
            try:
                return datetime.datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat()
            except ValueError:
                return ""
    return ""


class AskBody(BaseModel):
    question: str
    language: str = "English"


class AdviceBody(BaseModel):
    text: str


class QuestionBody(BaseModel):
    question: str


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
    filed = analysis["filed_date"] or _find_date(text) or now[:10]
    timeline.add_event(
        "filed", f"Filed: {file.filename} ({analysis['doc_type']})", filed)
    for ev in analysis["events"]:
        timeline.add_event("case_event", ev["event"], ev["date"])
    if facts.get("deadline") and facts["deadline"] != "Not stated":
        when = _find_date(facts["deadline"], text) or now
        timeline.add_event("case_date", f"Deadline: {facts['deadline']}", when)

    created = deadlines.apply(analysis["doc_type"], filed, file.filename)
    satisfied = obligations.try_satisfy(analysis["doc_type"])
    for fault in analysis["faults"]:
        questions.add(
            f"This {analysis['doc_type']} says: \"{fault['quote']}\" "
            f"({fault['category']}, regarding {fault['who']}). "
            "Ask your attorney what happened here.",
            source=file.filename, context_quote=fault["quote"])

    return {"key_facts": facts, "chunks_added": len(chunks),
            "doc_type": analysis["doc_type"], "filed_date": filed,
            "events_added": len(analysis["events"]),
            "presumptive_deadlines": created,
            "obligations_satisfied": satisfied,
            "faults_flagged": analysis["faults"]}


@app.post("/api/ask")
async def ask(body: AskBody):
    return rag.answer(body.question, body.language)


@app.get("/api/timeline")
async def get_timeline():
    return {"events": timeline.list_events()}


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


@app.get("/api/warnings")
async def get_warnings():
    return {"warnings": obligations.warnings()}


@app.post("/api/obligations/satisfy")
async def satisfy_obligation(body: IdBody):
    obligations.satisfy(body.id)
    return {"warnings": obligations.warnings()}


@app.get("/")
async def index():
    return FileResponse("web/index.html")
