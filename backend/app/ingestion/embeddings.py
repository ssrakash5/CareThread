"""
Deterministic local embedding stand-in for Bedrock embeddings.

Hackathon-local: no external API/model download. Uses a hashing-trick
bag-of-words vector (stable, dependency-free) so patient-scoped semantic
retrieval and matching still work end-to-end. Swap for a Bedrock/other
embedding call later behind this same function signature.
"""
import hashlib
import math
import re
from typing import List

from app.config import settings

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def embed_text(text: str) -> List[float]:
    dim = settings.embedding_dim
    vec = [0.0] * dim
    for tok in _tokens(text):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h // dim) % 2 == 0 else -1.0
        vec[idx] += sign

    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
