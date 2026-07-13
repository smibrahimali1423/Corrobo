from chunking import chunk_text


def test_short_text_produces_single_chunk():
    text = "Patients were randomized. The primary endpoint was survival."
    chunks = chunk_text(text, max_tokens=200)
    assert len(chunks) == 1
    assert "randomized" in chunks[0]
    assert "survival" in chunks[0]


def test_long_text_splits_into_multiple_chunks():
    sentence = (
        "The trial enrolled two hundred and forty patients across twelve "
        "different clinical sites nationwide. "
    )
    text = sentence * 20
    chunks = chunk_text(text, max_tokens=50, overlap_sentences=0)
    assert len(chunks) > 1


def test_overlap_carries_a_sentence_into_the_next_chunk():
    sentences = [
        f"Sentence {i} describes an independent clinical finding in detail."
        for i in range(15)
    ]
    text = " ".join(sentences)
    chunks = chunk_text(text, max_tokens=30, overlap_sentences=1)
    assert len(chunks) > 1

    overlap_found = any(
        sentence in chunks[i] and sentence in chunks[i + 1]
        for i in range(len(chunks) - 1)
        for sentence in sentences
    )
    assert overlap_found


def test_oversized_sentence_is_split_without_mangling_text():
    long_sentence = "UPPERCASE " * 300 + "period."
    chunks = chunk_text(long_sentence, max_tokens=50)
    assert len(chunks) > 1
    reconstructed = "".join(chunks)
    # Proves offset-based slicing is used instead of tokenizer.decode(),
    # which would lowercase this text.
    assert "UPPERCASE" in reconstructed
    assert "uppercase" not in reconstructed


def test_clinical_abbreviation_not_split():
    text = "Dr. Smith prescribed 500mg p.o. daily for the patient."
    chunks = chunk_text(text, max_tokens=200)
    assert len(chunks) == 1
    assert chunks[0] == text
