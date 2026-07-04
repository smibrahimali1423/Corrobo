import nltk
from nltk.tokenize.punkt import PunktParameters, PunktSentenceTokenizer
from transformers import AutoTokenizer

try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab")

_CLINICAL_ABBREVIATIONS = {
    "p.o",
    "b.i.d",
    "t.i.d",
    "q.i.d",
    "q.d",
    "q.h",
    "i.v",
    "i.m",
    "s.c",
    "p.r.n",
    "e.g",
    "i.e",
    "vs",
    "dr",
    "mr",
    "mrs",
    "ms",
    "et al",
}

_punkt_params = PunktParameters()
_punkt_params.abbrev_types.update(_CLINICAL_ABBREVIATIONS)
_SENT_TOKENIZER = PunktSentenceTokenizer(_punkt_params)

_TOKENIZER = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")


def _token_count(text: str) -> int:
    return len(_TOKENIZER.encode(text, add_special_tokens=False))


def _split_oversized_sentence(sentence: str, max_tokens: int) -> list[str]:
    encoding = _TOKENIZER(sentence, add_special_tokens=False, return_offsets_mapping=True)
    offsets = encoding["offset_mapping"]
    windows = [offsets[i : i + max_tokens] for i in range(0, len(offsets), max_tokens)]
    return [
        sentence[window[0][0] : window[-1][1]].strip() for window in windows if window
    ]


def chunk_text(
    text: str, max_tokens: int = 200, overlap_sentences: int = 1
) -> list[str]:
    sentences = _SENT_TOKENIZER.tokenize(text)
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = _token_count(sentence)

        if sentence_tokens > max_tokens:
            if current:
                chunks.append(" ".join(current))
                current = []
                current_tokens = 0
            chunks.extend(_split_oversized_sentence(sentence, max_tokens))
            continue

        if current_tokens + sentence_tokens > max_tokens and current:
            chunks.append(" ".join(current))
            overlap = current[-overlap_sentences:] if overlap_sentences else []
            current = list(overlap)
            current_tokens = sum(_token_count(s) for s in current)

        current.append(sentence)
        current_tokens += sentence_tokens

    if current:
        chunks.append(" ".join(current))

    return chunks
