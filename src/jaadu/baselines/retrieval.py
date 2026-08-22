from __future__ import annotations

from collections import Counter
import re
from jaadu.ingestion.documents import documents_as_of

KEYS = (
    "drought",
    "deficit",
    "seca",
    "below-normal",
    "el nino",
    "el niño",
    "reservoir",
    "kharif",
    "cantareira",
    "monsoon",
)


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Záéíóúñãõç]{3,}", text.lower())


def score_document(doc: dict, query_tokens: set[str]) -> float:
    toks = tokenize(doc.get("text", "") + " " + doc.get("title", ""))
    if not toks:
        return 0.0
    counts = Counter(toks)
    overlap = sum(counts[t] for t in query_tokens if t in counts)
    key_hits = sum(1 for k in KEYS if k in (doc.get("text", "").lower()))
    return overlap / len(toks) + 0.15 * key_hits


def retrieval_baseline(as_of: str, geo_id: str) -> dict:
    docs = documents_as_of(as_of)
    query = set(tokenize(geo_id.replace("_", " ") + " drought rainfall reservoir crop"))
    ranked = sorted(((score_document(d, query), d) for d in docs), key=lambda x: -x[0])
    hits = [d["doc_id"] for (s, d) in ranked if s > 0]
    alert = any(k in (d.get("text", "").lower() + d.get("title", "").lower()) for d in docs for k in KEYS)
    return {
        "name": "dated_document_retrieval",
        "alert": bool(alert and hits),
        "score": float(ranked[0][0]) if ranked else 0.0,
        "docs": hits[:8],
        "method": "publication-date-filtered keyword/overlap retrieval. Not a generative model and not numeric.",
    }
