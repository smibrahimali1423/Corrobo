from fastapi import Depends, FastAPI
from google import genai
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Submission
from schemas import SubmissionCreate, SubmissionOut

Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get("/")
def read_root():
    return {"status": "running"}


@app.get("/llm-ping")
def llm_ping():
    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents="Reply with a single word: pong"
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
    return submission


@app.get("/submissions", response_model=list[SubmissionOut])
def list_submissions(db: Session = Depends(get_db)):
    return db.execute(select(Submission)).scalars().all()
