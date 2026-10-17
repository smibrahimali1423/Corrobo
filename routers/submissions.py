import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from chunking import chunk_text
from claims import extract_claims
from config import get_settings
from database import get_db
from deps import get_current_user, require_llm
from embeddings import delete_chunks, retrieve_relevant_chunks, store_chunks
from judge import judge_claim
from models import CheckRun, ClaimResult, Submission, User
from schemas import (
    CheckResult,
    CheckRunOut,
    ClaimCheck,
    SubmissionCreate,
    SubmissionDetail,
    SubmissionListItem,
    SubmissionOut,
)

logger = logging.getLogger("corrobo")

router = APIRouter(prefix="/submissions", tags=["submissions"])


def _default_title(summary: str, max_len: int = 60) -> str:
    first_line = summary.strip().splitlines()[0] if summary.strip() else ""
    if len(first_line) <= max_len:
        return first_line or "Untitled submission"
    return first_line[: max_len - 1].rstrip() + "…"


def _get_owned_submission(db: Session, user: User, submission_id: int) -> Submission:
    submission = db.get(Submission, submission_id)
    # 404 (not 403) for other users' submissions, so ids don't leak existence.
    if submission is None or submission.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    return submission


@router.post("", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
def create_submission(
    payload: SubmissionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    submission = Submission(
        user_id=user.id,
        title=(payload.title or "").strip() or _default_title(payload.summary),
        source_document=payload.source_document,
        summary=payload.summary,
    )
    db.add(submission)
    db.flush()  # assigns submission.id without committing

    try:
        chunks = chunk_text(submission.source_document)
        store_chunks(submission.id, chunks)
    except Exception as exc:
        db.rollback()
        logger.exception("Indexing failed for new submission")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not index the source document (embedding model unavailable?)",
        ) from exc

    submission.chunk_count = len(chunks)
    db.commit()
    db.refresh(submission)
    return submission


@router.get("", response_model=list[SubmissionListItem])
def list_submissions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(
        select(Submission, func.count(CheckRun.id))
        .outerjoin(CheckRun, CheckRun.submission_id == Submission.id)
        .where(Submission.user_id == user.id)
        .group_by(Submission.id)
        .order_by(Submission.created_at.desc(), Submission.id.desc())
    ).all()
    return [
        SubmissionListItem(
            id=submission.id,
            title=submission.title,
            summary=submission.summary,
            chunk_count=submission.chunk_count,
            created_at=submission.created_at,
            check_count=check_count,
        )
        for submission, check_count in rows
    ]


@router.get("/{submission_id}", response_model=SubmissionDetail)
def get_submission(
    submission_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return _get_owned_submission(db, user, submission_id)


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_submission(
    submission_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    submission = _get_owned_submission(db, user, submission_id)
    db.delete(submission)
    db.commit()
    try:
        delete_chunks(submission_id)
    except Exception:
        # Orphaned vectors are harmless (retrieval is always filtered by an
        # owned submission_id), so don't fail the request over cleanup.
        logger.exception("Failed to delete chunks for submission %s", submission_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@router.post(
    "/{submission_id}/check",
    response_model=CheckResult,
    dependencies=[Depends(require_llm)],
)
def check_claim(
    submission_id: int,
    payload: ClaimCheck,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_submission(db, user, submission_id)
    return _check_single_claim(submission_id, payload.claim)


@router.post(
    "/{submission_id}/check-summary",
    response_model=CheckRunOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_llm)],
)
def check_summary(
    submission_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    submission = _get_owned_submission(db, user, submission_id)
    settings = get_settings()

    try:
        claims = extract_claims(submission.summary)
    except Exception as exc:
        logger.exception("Claim extraction failed for submission %s", submission_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Claim extraction failed: the LLM provider returned an error.",
        ) from exc

    # Cost guard: each claim is one LLM call.
    claims = claims[: settings.max_claims_per_check]
    results = [_check_single_claim(submission_id, claim) for claim in claims]

    run = CheckRun(submission_id=submission.id, model=settings.gemini_model)
    run.results = [
        ClaimResult(
            position=i,
            claim=r.claim,
            verdict=r.verdict,
            reason=r.reason,
            evidence=r.evidence,
        )
        for i, r in enumerate(results)
    ]
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
