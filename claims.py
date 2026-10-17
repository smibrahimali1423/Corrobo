from google import genai
from pydantic import BaseModel

from config import get_settings

_CLAIM_EXTRACTION_PROMPT = """Break the following summary into a list of standalone, \
atomic factual claims. Each claim should be checkable independently.

SUMMARY:
{summary}
"""


class ClaimList(BaseModel):
    claims: list[str]


def extract_claims(summary: str) -> list[str]:
    prompt = _CLAIM_EXTRACTION_PROMPT.format(summary=summary)

    client = genai.Client()
    response = client.models.generate_content(
        model=get_settings().gemini_model,
        contents=prompt,
        config={"response_mime_type": "application/json", "response_schema": ClaimList},
    )
    if not isinstance(response.parsed, ClaimList):
        raise ValueError("Gemini returned no parseable claim list")
    return response.parsed.claims
