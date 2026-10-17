from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="Untitled submission")
    source_document: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped[User] = relationship(back_populates="submissions")
    check_runs: Mapped[list["CheckRun"]] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
        order_by="CheckRun.created_at.desc()",
    )


class CheckRun(Base):
    """One execution of the full check-summary pipeline for a submission."""

    __tablename__ = "check_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), index=True
    )
    model: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    submission: Mapped[Submission] = relationship(back_populates="check_runs")
    results: Mapped[list["ClaimResult"]] = relationship(
        back_populates="check_run",
        cascade="all, delete-orphan",
        order_by="ClaimResult.position",
    )


class ClaimResult(Base):
    __tablename__ = "claim_results"
    __table_args__ = (
        CheckConstraint(
            "verdict IN ('SUPPORTED', 'CONTRADICTED', 'UNVERIFIABLE', 'ERROR')",
            name="ck_claim_results_verdict",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    check_run_id: Mapped[int] = mapped_column(
        ForeignKey("check_runs.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    claim: Mapped[str] = mapped_column(Text)
    verdict: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list[str]] = mapped_column(JSONB, default=list)

    check_run: Mapped[CheckRun] = relationship(back_populates="results")
