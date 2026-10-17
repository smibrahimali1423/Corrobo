# Corrobo

**Corrobo checks whether an AI-generated summary is actually supported by its source document.**

Paste a source document (a clinical note, a paper abstract, …) and a summary of it. Corrobo
breaks the summary into atomic claims, retrieves the most relevant passages of the source for
each claim (RAG), and asks an LLM judge whether each claim is **supported**, **contradicted**, or
**unverifiable** from the evidence alone.

It grew out of MSc thesis work on MedHAL (hallucination detection in clinical language models
with a fine-tuned BioClinicalBERT), recast as a live tool built on modern LLM APIs and retrieval.

## Architecture

```mermaid
flowchart LR
    UI[React SPA] -->|/api, JWT| API[FastAPI]
    API --> PG[(PostgreSQL<br/>users, submissions,<br/>check runs, results)]
    API -->|chunk + embed<br/>MiniLM-L6-v2| CH[(ChromaDB<br/>chunk vectors)]
    API -->|extract claims,<br/>judge each claim| GM[Gemini API]
```

**Submit**: the source is split into ~200-token sentence-aware chunks (`chunking.py`), embedded
with `sentence-transformers/all-MiniLM-L6-v2`, and stored in ChromaDB tagged with the submission
id (`embeddings.py`).

**Check**: Gemini extracts atomic claims from the summary (`claims.py`). For each claim, the top-5
chunks of *that* submission are retrieved, and Gemini judges the claim against only that evidence
(`judge.py`). The run and each verdict are saved in Postgres so results can be revisited.

A failure on one claim becomes an `ERROR` verdict for that claim and doesn't discard the rest. With
no `GEMINI_API_KEY`, everything except the LLM steps still works (see
[Running without a Gemini key](#running-without-a-gemini-key)).

| Layer | Tech |
|---|---|
| Frontend | React 18, TypeScript, Vite, React Router |
| Backend | FastAPI, SQLAlchemy 2, Alembic, pydantic-settings |
| Auth | Email/password (bcrypt) and JWT bearer tokens |
| Data | PostgreSQL 16, ChromaDB (embedded) |
| ML | sentence-transformers (MiniLM), NLTK Punkt, Google Gemini |
| Ops | Docker, docker-compose, GitHub Actions, Terraform (AWS EC2), Caddy |

## Quick start (Docker)

The fastest way to run everything: Postgres, the API, and the built UI in one container.

```bash
cp .env.example .env          # optionally set GEMINI_API_KEY
docker compose up --build
```

Open <http://localhost:8000> and sign in with the seeded demo account **demo@corrobo.dev** /
**corrobo-demo**, or register a new one. API docs are at <http://localhost:8000/docs>.

> The first build downloads torch (CPU) and the embedding model, which takes a few minutes. The
> dev compose seeds the demo account (`SEED_DEMO=true`). If you have an old `pgdata` volume from
> before migrations existed, reset it with `docker compose down -v`.

## Run locally (without Docker)

Prerequisites: Python 3.12, Node 22, and PostgreSQL 16.

**1. Database.** Use any local Postgres, or start only the compose one (it listens on port 5544):

```bash
docker compose up -d db
# then in .env: DATABASE_URL=postgresql://corrobo:changeme@localhost:5544/corrobo
```

Or create the role and database yourself:

```sql
CREATE USER corrobo WITH PASSWORD 'changeme' CREATEDB;
CREATE DATABASE corrobo OWNER corrobo;
CREATE DATABASE corrobo_test OWNER corrobo;  -- for the test suite
```

**2. Backend.**

```bash
python3.12 -m venv .venv && source .venv/bin/activate
# CPU-only torch first (the default wheel bundles ~3 GB of CUDA libraries)
pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.1
pip install -r requirements-dev.txt

cp .env.example .env            # set DATABASE_URL; GEMINI_API_KEY optional
alembic upgrade head            # create/upgrade the schema
python seed.py                  # optional: demo user + sample submissions
uvicorn main:app --reload       # http://localhost:8000
```

**3. Frontend** (dev server with hot reload; it proxies `/api` to port 8000):

```bash
cd frontend
npm ci
npm run dev                     # http://localhost:5173
```

For a production-style single server, run `npm run build`; FastAPI then serves `frontend/dist`
at <http://localhost:8000>.

## Running without a Gemini key

`GEMINI_API_KEY` is optional. Without it:

- `GET /api/health` reports `"llm_configured": false`, and the UI shows a banner and disables
  **Run check**.
- `POST …/check-summary`, `POST …/check` and `GET /api/llm-ping` return **503** with a clear
  message instead of failing obscurely.
- Registration, login, creating and indexing submissions, browsing past results, and deleting all
  keep working. The seeded demo data includes a precomputed check run, so there is something to
  look at.

## Tests, lint, typecheck

```bash
# Backend: needs the corrobo_test database (override with TEST_DATABASE_URL)
pytest                 # builds the schema via the real Alembic migrations; Gemini is mocked
ruff check .
mypy .

# Frontend
cd frontend && npm run lint && npm run typecheck && npm test

# Infrastructure (no AWS credentials needed: the AWS provider is mocked)
cd infra/terraform && terraform init -backend=false && terraform validate && terraform test
```

Tests never call Gemini: the LLM is mocked at the SDK boundary (`genai.Client`) or at the
pipeline functions. API tests replace chunking and embedding so they don't load ML models. The
ChromaDB logic is tested against a real (temporary) Chroma store with a deterministic fake
embedder, and the chunking tests use the real tokenizer. CI runs all of the above plus a Docker
image build.

## API

All routes are under `/api`. Everything except `health`, `auth/register` and `auth/login`
requires `Authorization: Bearer <token>`.

| Method | Path | Description |
|---|---|---|
| GET | `/health` | DB status and whether the LLM is configured |
| POST | `/auth/register` | `{email, password}` → token and user |
| POST | `/auth/login` | `{email, password}` → token and user |
| GET | `/auth/me` | Current user |
| POST | `/submissions` | `{title?, source_document, summary}`: saves, chunks and indexes |
| GET | `/submissions` | Your submissions (newest first) with check counts |
| GET | `/submissions/{id}` | Submission and all its check runs |
| DELETE | `/submissions/{id}` | Delete the submission, its runs and its vectors |
| POST | `/submissions/{id}/check-summary` | Run the full pipeline and persist the run (LLM) |
| POST | `/submissions/{id}/check` | `{claim}`: check one ad-hoc claim, not persisted (LLM) |
| GET | `/llm-ping` | Gemini connectivity check (LLM) |

Other users' submissions return 404, not 403, so their ids don't reveal that they exist.

## Configuration

All settings are environment variables (see `.env.example` and `config.py`):

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql://corrobo:changeme@localhost:5432/corrobo` | psycopg 3 driver |
| `GEMINI_API_KEY` | *(empty)* | Optional; LLM features are disabled without it |
| `GEMINI_MODEL` | `gemini-3.5-flash` | |
| `JWT_SECRET` | *(random per process)* | **Set this in production** |
| `JWT_EXPIRE_MINUTES` | `1440` | |
| `MAX_CLAIMS_PER_CHECK` | `25` | Cost guard: each claim is one LLM call |
| `CHROMA_PATH` | `./chroma_data` | |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated |

## Deployment

The app is deployed to a single AWS EC2 instance running docker-compose (Postgres, API, and
Caddy for automatic HTTPS), provisioned with Terraform and deployed from GitHub Actions via OIDC
and SSM, with no long-lived AWS keys. See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for the
step-by-step guide.

## Project layout

```
main.py              FastAPI app: mounts /api routers and serves the built SPA
config.py            Settings (env vars)
database.py          SQLAlchemy engine/session
models.py            ORM models: User, Submission, CheckRun, ClaimResult
schemas.py           Pydantic request/response models
security.py          bcrypt hashing, JWT create/verify
deps.py              Auth and "LLM configured" dependencies
routers/             auth, submissions, system (health, llm-ping)
chunking.py          Sentence-aware, token-bounded chunking
embeddings.py        MiniLM embeddings and ChromaDB store/retrieve/delete
claims.py, judge.py  Gemini claim extraction and claim judging
seed.py              Demo data
migrations/          Alembic migrations
tests/               pytest suite
frontend/            React + TypeScript SPA
deploy/              Production compose file, Caddyfile, deploy.sh (copied to EC2)
infra/terraform/     AWS infrastructure as code (and offline tests)
docs/DEPLOYMENT.md   Step-by-step AWS deployment guide
DECISIONS.md         Design decisions and trade-offs
```
