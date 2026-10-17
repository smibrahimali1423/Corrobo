import logging
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from config import get_settings
from routers import auth, submissions, system

logging.basicConfig(level=logging.INFO)

# Schema is managed by Alembic (`alembic upgrade head`), not create_all().
app = FastAPI(title="Corrobo", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")
api.include_router(system.router)
api.include_router(auth.router)
api.include_router(submissions.router)
app.include_router(api)


def _frontend_dist() -> Path:
    return Path(get_settings().frontend_dist).resolve()


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str):
    """Serve the built React app, falling back to index.html for client routes."""
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")

    dist = _frontend_dist()
    index = dist / "index.html"
    if not index.is_file():
        return {"status": "running", "detail": "Frontend not built; API docs at /docs"}

    candidate = (dist / full_path).resolve()
    if full_path and candidate.is_file() and candidate.is_relative_to(dist):
        return FileResponse(candidate)
    return FileResponse(index)
