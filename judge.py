from typing import Literal

from google import genai
from pydantic import BaseModel

_JUDGE_PROMPT = """You are a fact-checking assistant. You are given EVIDENCE excerpts \
from a source document, and a CLAIM taken from a summary of that document.

Judge whether the CLAIM is supported by the EVIDENCE. Use only the EVIDENCE below \
-- do not rely on outside knowledge, even if you know it to be true.

EVIDENCE:
{evidence}

CLAIM:
{claim}

Respond with a verdict of exactly one of: SUPPORTED, CONTRADICTED, UNVERIFIABLE.
- SUPPORTED: the evidence confirms the claim.
- CONTRADICTED: the evidence directly contradicts the claim.
- UNVERIFIABLE: the evidence does not contain enough information to judge the claim
  either way.

Also give a one-sentence reason for the verdict.
"""


class Judgment(BaseModel):
    verdict: Literal["SUPPORTED", "CONTRADICTED", "UNVERIFIABLE"]
    reason: str


def judge_claim(claim: str, evidence: list[str]) -> Judgment:
    evidence_block = "\n".join(f"- {chunk}" for chunk in evidence)
    if not evidence_block:
        evidence_block = "(no evidence retrieved)"

    prompt = _JUDGE_PROMPT.format(evidence=evidence_block, claim=claim)

    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config={"response_mime_type": "application/json", "response_schema": Judgment},
    )
    return response.parsed
