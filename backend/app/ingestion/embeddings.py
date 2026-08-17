"""
Chunk embeddings.

``embed_text`` dispatches on ``settings.ai_provider``:
  * ``bedrock`` -> Amazon Titan Text Embeddings v2 (see app/ai/bedrock.py)
  * ``local``   -> deterministic hashing-trick bag-of-words vector (no network)

Both return unit-length vectors of ``settings.embedding_dim`` so
``cosine_similarity`` (a plain dot product) works for either. A Bedrock
failure falls back to the local vector for that chunk and logs a warning.
"""
import hashlib
import logging
import math
import re
from typing import List

from app.config import settings

log = logging.getLogger("carethread.embeddings")
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def embed_text_local(text: str) -> List[float]:
    dim = settings.embedding_dim
    vec = [0.0] * dim
    for tok in _tokens(text):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h // dim) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed_text(text: str) -> List[float]:
    if settings.ai_provider == "bedrock":
        try:
            from app.ai.bedrock import embed_text_bedrock
            return embed_text_bedrock(text)
        except Exception as e:  # noqa: BLE001
            log.warning("Bedrock embedding failed (%s); using local embedding", e)
    return embed_text_local(text)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
