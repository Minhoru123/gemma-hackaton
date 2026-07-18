import os
import re
import datetime
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from app import store, timeline, ingest, extract, rag, ollama_client

app = FastAPI(title="Case Companion")
app.mount("/web", StaticFiles(directory="web"), name="web")
UPLOAD_DIR = "uploads"


@app.on_event("startup")
def _startup():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    store.init_db()
    timeline.init()
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
        # Sort by a real calendar date if we can find one (in the deadline text or the
        # document); otherwise fall back to the upload time so it still appears in order.
        when = _find_date(facts["deadline"], text) or now
        timeline.add_event("case_date", f"Deadline: {facts['deadline']}", when)
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
