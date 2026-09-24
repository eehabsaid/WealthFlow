"""Semantic retrieval: embeds text via Ollama's /api/embeddings and ranks
candidates by cosine similarity. Used as a bonus signal alongside (not a
replacement for) the keyword scoring in providers/registry/scoring.py and
context_builder_service/service.py, so an embedding-service outage degrades
to the existing keyword behavior instead of breaking retrieval.

Candidate embeddings are cached in-process (module-level dict) since the
candidate set — provider/service descriptions — doesn't change at runtime;
only the query needs embedding on each call.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from core.integrations.provider_utils import make_json_http_request
from core.models import AppSettings

logger = logging.getLogger(__name__)

DEFAULT_EMBED_MODEL = "nomic-embed-text"
_EMBED_TIMEOUT_SECONDS = 5

_candidate_cache: dict[str, list[float]] = {}


def _embed(text: str) -> list[float] | None:
    """Never raises — returns None on any failure (model not pulled,
    Ollama unreachable, timeout, malformed response)."""
    text = (text or "").strip()
    if not text:
        return None
    url = AppSettings.get("ai_ollama_url", "http://localhost:11434").rstrip("/")
    model = AppSettings.get("ai_embed_model", DEFAULT_EMBED_MODEL)
    data, status_code, error = make_json_http_request(
        f"{url}/api/embeddings",
        method="POST",
        payload={"model": model, "prompt": text},
        timeout=_EMBED_TIMEOUT_SECONDS,
    )
    if error or status_code != 200 or not isinstance(data, dict):
        logger.info("Embedding call failed, falling back to keyword scoring only: %s", error)
        return None
    vec = data.get("embedding")
    if isinstance(vec, list) and vec:
        return vec
    return None


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def semantic_scores(query: str, candidates: dict[str, str]) -> dict[str, float] | None:
    """candidates: {key: description_text}. Returns {key: similarity in
    [0,1]} or None if the embedding service is unavailable (caller should
    fall back to keyword-only scoring in that case)."""
    q_vec = _embed(query)
    if q_vec is None:
        return None

    scores: dict[str, float] = {}
    for key, desc in candidates.items():
        c_vec = _candidate_cache.get(key)
        if c_vec is None:
            c_vec = _embed(desc)
            if c_vec is None:
                return None
            _candidate_cache[key] = c_vec
        scores[key] = max(0.0, _cosine(q_vec, c_vec))
    return scores
