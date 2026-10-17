import os
import tempfile

# Must run before any app module is imported: config/database read these at import.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://corrobo:changeme@localhost:5432/corrobo_test"
)
os.environ["GEMINI_API_KEY"] = ""  # tests never hit the real Gemini API
os.environ["JWT_SECRET"] = "test-secret-not-for-production-use-0123456789"
os.environ["CHROMA_PATH"] = tempfile.mkdtemp(prefix="corrobo-chroma-")
os.environ["FRONTEND_DIST"] = tempfile.mkdtemp(prefix="corrobo-dist-")

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from config import get_settings  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from main import app  # noqa: E402
from tests.helpers import register  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _migrated_database():
    """Build the schema with the real Alembic migrations (so they're tested too)."""
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(Config("alembic.ini"), "head")
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def llm_enabled(monkeypatch):
    """Pretend a Gemini key is configured. Gemini calls themselves must still be mocked."""
    monkeypatch.setattr(get_settings(), "gemini_api_key", "fake-key-for-tests")


@pytest.fixture()
def mock_indexing(monkeypatch):
    """Replace chunking + vector storage so API tests don't load ML models."""
    stored: dict[int, list[str]] = {}

    def fake_store(submission_id, chunks):
        stored[submission_id] = chunks

    monkeypatch.setattr(
        "routers.submissions.chunk_text", lambda text, **kwargs: ["chunk one", "chunk two"]
    )
    monkeypatch.setattr("routers.submissions.store_chunks", fake_store)
    monkeypatch.setattr("routers.submissions.delete_chunks", lambda sid: stored.pop(sid, None))
    return stored


@pytest.fixture()
def auth_headers(client):
    token = register(client)["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def make_submission(client, auth_headers, mock_indexing):
    def _make(headers=None, **overrides):
        body = {"source_document": "Some source text.", "summary": "A summary."} | overrides
        resp = client.post("/api/submissions", json=body, headers=headers or auth_headers)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make
