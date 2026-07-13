from fastapi import Depends, FastAPI
from google import genai
from sqlalchemy import select
from sqlalchemy.orm import Session

from chunking import chunk_text
from database import Base, engine, get_db
from embeddings import retrieve_relevant_chunks, store_chunks
from judge import judge_claim
from models import Submission
from schemas import CheckResult, ClaimCheck, SubmissionCreate, SubmissionOut

Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get("/")
def read_root():
    return {"status": "running"}


@app.get("/llm-ping")
def llm_ping():
    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-3.5-flash", contents="Reply with a single word: pong"
    )
    return {"reply": response.text}


@app.post("/submissions", response_model=SubmissionOut)
def create_submission(payload: SubmissionCreate, db: Session = Depends(get_db)):
    submission = Submission(
        source_document=payload.source_document, summary=payload.summary
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    chunks = chunk_text(submission.source_document)
    store_chunks(submission.id, chunks)

    return submission


@app.get("/submissions", response_model=list[SubmissionOut])
def list_submissions(db: Session = Depends(get_db)):
    return db.execute(select(Submission)).scalars().all()


@app.post("/submissions/{submission_id}/check", response_model=CheckResult)
def check_claim(submission_id: int, payload: ClaimCheck):
    # Judges one claim at a time; splitting a full summary into individual
    # claims automatically isn't built yet.
    evidence = retrieve_relevant_chunks(submission_id, payload.claim)
    judgment = judge_claim(payload.claim, evidence)
    return CheckResult(
        claim=payload.claim,
        verdict=judgment.verdict,
        reason=judgment.reason,
        evidence=evidence,
    )
