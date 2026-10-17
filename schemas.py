from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field

Verdict = Literal["SUPPORTED", "CONTRADICTED", "UNVERIFIABLE", "ERROR"]

MAX_SOURCE_CHARS = 200_000
MAX_SUMMARY_CHARS = 20_000


# --- auth ---------------------------------------------------------------------


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- submissions ----------------------------------------------------------------


class SubmissionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    source_document: str = Field(min_length=1, max_length=MAX_SOURCE_CHARS)
    summary: str = Field(min_length=1, max_length=MAX_SUMMARY_CHARS)


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source_document: str
    summary: str
    chunk_count: int
    created_at: datetime


class SubmissionListItem(BaseModel):
    id: int
    title: str
    summary: str
    chunk_count: int
    created_at: datetime
    check_count: int


# --- checks ---------------------------------------------------------------------


class ClaimCheck(BaseModel):
    claim: str = Field(min_length=1, max_length=2_000)


class CheckResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    claim: str
    verdict: Verdict
    reason: str
    evidence: list[str]


class CheckRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submission_id: int
    model: str
    created_at: datetime
    results: list[CheckResult]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def verdict_counts(self) -> dict[str, int]:
        counts = {"SUPPORTED": 0, "CONTRADICTED": 0, "UNVERIFIABLE": 0, "ERROR": 0}
        for result in self.results:
            counts[result.verdict] += 1
        return counts


class SubmissionDetail(SubmissionOut):
    check_runs: list[CheckRunOut]


# --- system ---------------------------------------------------------------------


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    database: bool
    llm_configured: bool
    model: str
