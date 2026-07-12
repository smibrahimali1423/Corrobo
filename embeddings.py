import chromadb
from sentence_transformers import SentenceTransformer

_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
_CLIENT = chromadb.PersistentClient(path="./chroma_data")
_COLLECTION = _CLIENT.get_or_create_collection("chunks")


def store_chunks(submission_id: int, chunks: list[str]) -> None:
    if not chunks:
        return

    embeddings = _MODEL.encode(chunks).tolist()
    ids = [f"{submission_id}-{i}" for i in range(len(chunks))]
    metadatas = [{"submission_id": submission_id} for _ in chunks]

    _COLLECTION.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )


def retrieve_relevant_chunks(submission_id: int, claim: str, k: int = 5) -> list[str]:
    query_embedding = _MODEL.encode([claim]).tolist()

    results = _COLLECTION.query(
        query_embeddings=query_embedding,
        n_results=k,
        where={"submission_id": submission_id},
    )

    return results["documents"][0]
