"""Seed a demo account with example submissions and a precomputed check run.

Usage:  python seed.py
Idempotent: re-running does nothing if the demo user already exists.

The precomputed check run lets the UI show results even when no GEMINI_API_KEY
is configured. Its verdicts are illustrative demo data, not real model output.
"""

import logging
import os
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from chunking import chunk_text
from database import SessionLocal
from embeddings import store_chunks
from models import CheckRun, ClaimResult, Submission, User
from security import hash_password

logger = logging.getLogger("corrobo.seed")

DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "demo@corrobo.dev")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "corrobo-demo")

class Sample(TypedDict):
    title: str
    source_document: str
    summary: str
    # (claim, verdict, reason, evidence) tuples, or None to leave unchecked
    results: list[tuple[str, str, str, list[str]]] | None


SAMPLES: list[Sample] = [
    {
        "title": "Phase III trial of drug X in heart failure",
        "source_document": (
            "This randomized, double-blind, placebo-controlled phase III trial enrolled 240 "
            "patients with chronic heart failure across twelve clinical sites. Patients were "
            "randomized 1:1 to receive drug X 50mg p.o. b.i.d. or placebo for 52 weeks. "
            "The primary endpoint was all-cause mortality at one year. Mortality was 18% in "
            "the drug X group compared with 27% in the placebo group (hazard ratio 0.64, "
            "p = 0.03). The most common adverse event was mild dizziness, reported by 12% of "
            "patients receiving drug X and 5% receiving placebo. Two patients in the drug X "
            "group discontinued treatment because of hypotension. The authors concluded that "
            "drug X reduced one-year mortality but noted that larger trials are needed to "
            "confirm the effect in patients over 80 years old."
        ),
        "summary": (
            "A phase III trial of 240 heart failure patients found that drug X reduced "
            "one-year mortality from 27% to 18%. Drug X was given intravenously once daily. "
            "Dizziness was the most common side effect. The drug was proven effective in "
            "patients over 80."
        ),
        "results": [
            (
                "A phase III trial enrolled 240 heart failure patients.",
                "SUPPORTED",
                "The evidence states the phase III trial enrolled 240 patients with "
                "chronic heart failure.",
                [
                    "This randomized, double-blind, placebo-controlled phase III trial enrolled "
                    "240 patients with chronic heart failure across twelve clinical sites."
                ],
            ),
            (
                "Drug X reduced one-year mortality from 27% to 18%.",
                "SUPPORTED",
                "Mortality was 18% with drug X versus 27% with placebo at one year.",
                [
                    "Mortality was 18% in the drug X group compared with 27% in the placebo "
                    "group (hazard ratio 0.64, p = 0.03)."
                ],
            ),
            (
                "Drug X was given intravenously once daily.",
                "CONTRADICTED",
                "The source says drug X was given orally (p.o.) twice daily (b.i.d.).",
                [
                    "Patients were randomized 1:1 to receive drug X 50mg p.o. b.i.d. or placebo "
                    "for 52 weeks."
                ],
            ),
            (
                "Dizziness was the most common side effect.",
                "SUPPORTED",
                "Mild dizziness is reported as the most common adverse event.",
                [
                    "The most common adverse event was mild dizziness, reported by 12% of "
                    "patients receiving drug X and 5% receiving placebo."
                ],
            ),
            (
                "The drug was proven effective in patients over 80.",
                "CONTRADICTED",
                "The authors state larger trials are needed to confirm the effect in "
                "patients over 80.",
                [
                    "The authors concluded that drug X reduced one-year mortality but noted that "
                    "larger trials are needed to confirm the effect in patients over 80 years old."
                ],
            ),
        ],
    },
    {
        "title": "Discharge note: community-acquired pneumonia",
        "source_document": (
            "Mr. Jones, a 67-year-old man, was admitted with community-acquired pneumonia "
            "confirmed by chest X-ray showing right lower lobe consolidation. He was treated "
            "with ceftriaxone i.v. and azithromycin for three days, then switched to oral "
            "amoxicillin-clavulanate. His oxygen saturation improved from 89% on admission to "
            "96% on room air by day four. He was discharged on day five with instructions to "
            "complete a seven-day antibiotic course and to follow up with his GP in two weeks."
        ),
        "summary": (
            "A 67-year-old man with right lower lobe pneumonia was treated with IV "
            "antibiotics and discharged on day five. He has a history of COPD."
        ),
        "results": None,  # left unchecked so the demo user can run a check themselves
    },
]


def _index(submission: Submission) -> None:
    """Chunk + embed into Chroma; failures are logged, not fatal, for the seed."""
    try:
        chunks = chunk_text(submission.source_document)
        store_chunks(submission.id, chunks)
        submission.chunk_count = len(chunks)
    except Exception:
        logger.warning(
            "Could not index submission %s (embedding model unavailable?). "
            "It is saved, but retrieval will return no evidence until re-created.",
            submission.id,
            exc_info=True,
        )


def seed(db: Session, index: bool = True) -> User | None:
    """Create the demo user and samples. Returns the user, or None if already seeded."""
    if db.execute(select(User).where(User.email == DEMO_EMAIL)).scalar_one_or_none():
        return None

    user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD))
    db.add(user)
    db.flush()

    for sample in SAMPLES:
        submission = Submission(
            user_id=user.id,
            title=sample["title"],
            source_document=sample["source_document"],
            summary=sample["summary"],
        )
        db.add(submission)
        db.flush()
        if index:
            _index(submission)

        if sample["results"]:
            run = CheckRun(submission_id=submission.id, model="demo-seed")
            run.results = [
                ClaimResult(
                    position=i, claim=claim, verdict=verdict, reason=reason, evidence=evidence
                )
                for i, (claim, verdict, reason, evidence) in enumerate(sample["results"])
            ]
            db.add(run)

    db.commit()
    return user


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    with SessionLocal() as db:
        user = seed(db)
    if user is None:
        logger.info("Demo user %s already exists; nothing to do.", DEMO_EMAIL)
    else:
        logger.info("Seeded demo user %s (password: %s)", DEMO_EMAIL, DEMO_PASSWORD)


if __name__ == "__main__":
    main()
