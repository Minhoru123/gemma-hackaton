# Case Companion — 3-Minute Demo Script

**Track:** On-Device AI with Gemma 4. **Model runs fully local via Ollama. No cloud.**

## Setup (before judges arrive)

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    python scripts/build_corpus.py
    python -m uvicorn app.main:app --port 8000

Open http://localhost:8000. The first question is slower (model loads); ask one warm-up
question before the demo so the model is hot.

## The pitch (15 seconds)

"People in family-law cases or suing the state often can't afford a lawyer, may not have
reliable internet, and shouldn't have to hand their personal legal situation to a cloud
company. Case Companion explains their documents and rights, in plain English, on any
laptop, offline, for free."

## The demo (2.5 minutes)

1. **Upload** `samples/notice_of_hearing.txt` (drag onto the drop zone).
   - The **Key Facts card** fills in: summary, parties, deadline, action required, and a
     red **risk flag** ("Failure to file a response may result in a default judgment").
   - "Instantly, the scary letter is demystified."

2. **Ask:** "What happens if I miss the deadline to respond?"
   - A plain-English answer appears **with [Source N] citations**.
   - **Click a citation** -> the exact source snippet is revealed. "Every answer shows its
     receipts. It only speaks from the bundled legal reference, and cites it."

3. **Honesty guardrail — ask something off-topic:** "What's the weather tomorrow?"
   - It responds "I don't have information about that in your documents." "It refuses to
     make up legal facts."

4. **Spanish:** switch the language toggle to Spanish, re-ask a question.
   - Answers in Spanish. "Accessibility for non-English speakers."

5. **Timeline:** point at the Case Timeline — upload event + the extracted Aug 3 deadline,
   in order.

6. **THE MONEY SHOT — turn off WiFi (airplane mode ON), then ask another question.**
   - It still answers. The offline indicator turns green: "Offline — still working."
   - "This is the eligibility gate: Gemma is running entirely on this machine. No network."

## The vision (15 seconds)

"A legal-aid org or lawyer bundles the reference corpus into one file and ships it to a
client, who runs it on their own computer. The database file IS the shareable bundle."

## Data provenance answer (if asked)

"The case data is public-record — retrievable by case number from court filings. Our
on-device design is about access and dignity, not secrecy: it's free, private, and works
without internet."

## If the model is too slow on the demo machine

The app runs `gemma4:latest`. Ask a warm-up question before the demo so the model is
loaded and hot; the first answer after startup is always the slowest.
