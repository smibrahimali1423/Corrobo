from fastapi import APIRouter, Depends
from google import genai
from sqlalchemy import text
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from deps import get_current_user, require_llm
from schemas import Health

router = APIRouter(tags=["system"])


@router.get("/health", response_model=Health)
def health(db: Session = Depends(get_db)):
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        database_ok = True
    except Exception:
        database_ok = False

    return Health(
        status="ok" if database_ok else "degraded",
        database=database_ok,
        llm_configured=settings.llm_configured,
        model=settings.gemini_model,
    )


@router.get("/llm-ping", dependencies=[Depends(get_current_user), Depends(require_llm)])
def llm_ping():
    client = genai.Client()
    response = client.models.generate_content(
        model=get_settings().gemini_model, contents="Reply with a single word: pong"
    )
    return {"reply": response.text}
