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

# Raw cosine similarity from embedding models (nomic-embed-text included) is
# anisotropic: unrelated text pairs routinely score 0.4-0.6, not near 0. An
# absolute floor alone (SEMANTIC_MATCH_THRESHOLD) therefore isn't enough to
# tell "genuinely topical match" apart from "generic noise floor that happens
# to clear the floor" — confirmed in production: a nonsense query ("qzxjklm
# vwplotg") that should fall back to DEFAULT_CORE_SERVICES instead scored a
# false-positive semantic match against an unrelated provider. Requiring the
# top score to also clear the mean of all candidate scores by this margin
# filters out that "everything's about equally (ir)relevant" case while still
# passing through real topical matches, which normally separate from the pack.
SEMANTIC_MARGIN_OVER_MEAN = 0.08


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
    # Also require separation from the pack (see SEMANTIC_MARGIN_OVER_MEAN above): an
    # absolute floor alone still lets a uniformly-noisy score set through.
    values = list(sem_scores.values())
    mean_sim = sum(values) / len(values)
    for key, sim in sem_scores.items():
        if sim >= SEMANTIC_MATCH_THRESHOLD and sim >= mean_sim + SEMANTIC_MARGIN_OVER_MEAN:
            scores[key] = scores.get(key, 0.0) + sim * 3.0
