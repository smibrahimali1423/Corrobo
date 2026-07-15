FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download model weights/data at build time, not at container startup --
# keeps cold start fast and avoids depending on HF Hub / nltk's servers
# being reachable (and un-rate-limited) every time a container boots.
RUN python -c "import nltk; nltk.download('punkt_tab')"
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY . .

RUN useradd --create-home appuser \
    && mkdir -p /app/chroma_data \
    && chown -R appuser:appuser /app/chroma_data
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
