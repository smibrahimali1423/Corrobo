from functools import lru_cache

import chromadb
from sentence_transformers import SentenceTransformer

from config import get_settings

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


# Loaded lazily (on first use, then cached) rather than at import time, so the
# API can boot, and tests can import this module, without loading model weights.
@lru_cache
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(_MODEL_NAME)


@lru_cache
def _get_collection():
    client = chromadb.PersistentClient(path=get_settings().chroma_path)
    return client.get_or_create_collection("chunks")


def store_chunks(submission_id: int, chunks: list[str]) -> None:
    if not chunks:
        return

    embeddings = _get_model().encode(chunks).tolist()
    ids = [f"{submission_id}-{i}" for i in range(len(chunks))]
    metadatas = [{"submission_id": submission_id} for _ in chunks]

    _get_collection().upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )


def retrieve_relevant_chunks(submission_id: int, claim: str, k: int = 5) -> list[str]:
    query_embedding = _get_model().encode([claim]).tolist()

    results = _get_collection().query(
        query_embeddings=query_embedding,
        n_results=k,
        where={"submission_id": submission_id},
    )

    return results["documents"][0]


def delete_chunks(submission_id: int) -> None:
    _get_collection().delete(where={"submission_id": submission_id})
