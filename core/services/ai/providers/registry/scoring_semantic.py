"""Semantic bonus for provider relevance scoring (split out of scoring.py, 200-line rule)."""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# A keyword score at/above this means a term matched a provider's key/name (or several
# metadata terms hit): the lexical match is decisive and the embedding call (query embed +
# possible embed-model load/swap on Ollama) is skipped. Semantic scoring still runs when
# nothing matched lexically or only weakly, which is exactly what it exists for.
LEXICAL_DECISIVE_SCORE = 3.0
SEMANTIC_MATCH_THRESHOLD = 0.45


def apply_semantic_bonus(scores: dict[str, float], registry: dict[str, Any], query_str: str,
                         build_meta_text: Callable[[Any], str]) -> None:
    """Adds the semantic bonus to `scores` in place.

    Additive, not a replacement: if the embedding service is down, semantic_scores()
    returns None and behavior is identical to keyword-only scoring — never blocks a
    response on an outage. Skipped entirely when the lexical match is already decisive."""
    from core.services.ai.retrieval import embeddings as _emb
    from core.services.ai.retrieval import semantic_scores

    if max(scores.values(), default=0.0) >= LEXICAL_DECISIVE_SCORE:
        _emb.stats["skipped_lexical"] += 1
        return
    candidates = {key: build_meta_text(p) for key, p in registry.items()}
    try:
        sem_scores = semantic_scores(query_str, candidates)
    except Exception as exc:
        logger.info("Semantic scoring skipped for providers: %s", exc)
        return
    if not sem_scores:
        return
    # Only a real semantic match counts as a signal — a raw cosine score is rarely exactly
    # 0.0 even for unrelated text, so adding it unconditionally would defeat the
    # require_signal=True path (every provider would show weak positive "signal" again).
    for key, sim in sem_scores.items():
        if sim >= SEMANTIC_MATCH_THRESHOLD:
            scores[key] = scores.get(key, 0.0) + sim * 3.0
