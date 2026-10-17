# ---- Stage 1: build the React frontend ---------------------------------------
# Node is only needed at build time; the final image ships just the static files.
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python API (also serves the built frontend) --------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # Model/data caches live outside any user's $HOME, so files downloaded at
    # build time (as root) are found at runtime (as appuser).
    HF_HOME=/opt/hf \
    NLTK_DATA=/opt/nltk_data

WORKDIR /app

# CPU-only torch: the default PyPI wheel bundles ~3GB of CUDA libraries that a
# CPU EC2 instance never uses. Installed first so requirements.txt reuses it.
ARG TORCH_VERSION=2.14.1
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN pip install --index-url ${TORCH_INDEX_URL} "torch==${TORCH_VERSION}"

COPY requirements.txt .
RUN pip install -r requirements.txt

# Pre-download model weights/data at build time, not at container startup --
# keeps cold start fast and avoids depending on HF Hub / nltk's servers
# being reachable (and un-rate-limited) every time a container boots.
ARG PRELOAD_MODELS=true
RUN if [ "$PRELOAD_MODELS" = "true" ]; then \
      python -c "import nltk; nltk.download('punkt_tab', download_dir='/opt/nltk_data')" && \
      python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"; \
    fi
# Never call the HF Hub at runtime when the model was baked in. (If you build
# with PRELOAD_MODELS=false, also pass HF_HUB_OFFLINE=0 so it can download.)
ARG HF_HUB_OFFLINE=1
ENV HF_HUB_OFFLINE=${HF_HUB_OFFLINE}

COPY *.py alembic.ini docker-entrypoint.sh ./
COPY routers/ routers/
COPY migrations/ migrations/
COPY --from=frontend /frontend/dist ./frontend/dist

RUN useradd --create-home appuser \
    && mkdir -p /app/chroma_data \
    && chown -R appuser:appuser /app/chroma_data \
    && chmod +x docker-entrypoint.sh
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health', timeout=4)"

ENTRYPOINT ["./docker-entrypoint.sh"]
# One worker: Chroma's embedded PersistentClient is single-process.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
