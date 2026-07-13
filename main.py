from fastapi import Depends, FastAPI, HTTPException
from google import genai
from sqlalchemy import select
from sqlalchemy.orm import Session

from chunking import chunk_text
from claims import extract_claims
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


def _check_single_claim(submission_id: int, claim: str) -> CheckResult:
    try:
        evidence = retrieve_relevant_chunks(submission_id, claim)
        judgment = judge_claim(claim, evidence)
    except Exception as exc:
        # Broad catch is intentional: this wraps an external API call, and a
        # transient failure on one claim shouldn't discard already-successful
        # judgments for the other claims in the same /check-summary batch.
        return CheckResult(claim=claim, verdict="ERROR", reason=str(exc), evidence=[])

    return CheckResult(
        claim=claim,
        verdict=judgment.verdict,
        reason=judgment.reason,
        evidence=evidence,
    )


@app.post("/submissions/{submission_id}/check", response_model=CheckResult)
def check_claim(submission_id: int, payload: ClaimCheck):
    return _check_single_claim(submission_id, payload.claim)


@app.post("/submissions/{submission_id}/check-summary", response_model=list[CheckResult])
def check_summary(submission_id: int, db: Session = Depends(get_db)):
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    claims = extract_claims(submission.summary)
    return [_check_single_claim(submission_id, claim) for claim in claims]
