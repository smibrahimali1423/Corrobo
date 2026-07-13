from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SubmissionCreate(BaseModel):
    source_document: str
    summary: str


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_document: str
    summary: str
    created_at: datetime


class ClaimCheck(BaseModel):
    claim: str


class CheckResult(BaseModel):
    claim: str
    verdict: str
    reason: str
    evidence: list[str]
