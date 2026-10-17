"""Exercises the real ChromaDB store/retrieve/delete logic with a fake embedder.

The fake maps each text to a bag-of-letters vector: deterministic, offline, and
similar texts get similar vectors, which is all retrieval ordering needs here.
"""

import numpy as np
import pytest

import embeddings


class _FakeModel:
    def encode(self, texts):
        vectors = []
        for text in texts:
            v = np.zeros(26)
            for ch in text.lower():
                if "a" <= ch <= "z":
                    v[ord(ch) - ord("a")] += 1
            vectors.append(v / (np.linalg.norm(v) or 1))
        return np.array(vectors)


@pytest.fixture(autouse=True)
def fake_model(monkeypatch):
    monkeypatch.setattr(embeddings, "_get_model", lambda: _FakeModel())


def test_retrieve_is_scoped_to_submission():
    embeddings.store_chunks(101, ["aspirin reduces fever", "zzz unrelated"])
    embeddings.store_chunks(102, ["aspirin reduces fever in another doc"])

    results = embeddings.retrieve_relevant_chunks(101, "aspirin fever", k=5)

    assert set(results) == {"aspirin reduces fever", "zzz unrelated"}
    assert results[0] == "aspirin reduces fever"  # most similar first


def test_store_is_idempotent_upsert():
    embeddings.store_chunks(201, ["alpha", "beta"])
    embeddings.store_chunks(201, ["alpha", "beta"])
    assert len(embeddings.retrieve_relevant_chunks(201, "alpha", k=10)) == 2


def test_store_empty_chunks_is_noop():
    embeddings.store_chunks(301, [])
    assert embeddings.retrieve_relevant_chunks(301, "anything") == []


def test_delete_chunks_removes_only_that_submission():
    embeddings.store_chunks(401, ["one"])
    embeddings.store_chunks(402, ["two"])

    embeddings.delete_chunks(401)

    assert embeddings.retrieve_relevant_chunks(401, "one") == []
    assert embeddings.retrieve_relevant_chunks(402, "two") == ["two"]
