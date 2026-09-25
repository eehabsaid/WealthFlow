"""
Relevance scoring and data retrieval for the AI provider registry.

Split out of the former monolithic registry.py (200-line rule). Reads
the shared registry dict from __init__.py (this package's parent module)
via `from . import ...` — the dict object itself is mutated in place by
autodiscover_providers(), never reassigned, so this module's reference
to it always reflects the current registered providers.
"""

from __future__ import annotations

import logging
from typing import Any

from .scoring_semantic import apply_semantic_bonus

logger = logging.getLogger(__name__)


def _build_meta_text(provider: Any) -> str:
    """Collect provider metadata (key, name, capabilities) into one text
    blob — used both for keyword scoring and as the semantic-retrieval
    candidate description (see core/services/ai/retrieval/embeddings.py)."""
    meta_tokens: list[str] = [provider.key.lower(), provider.name.lower()]
    capabilities = provider.get_capabilities() or []
    for cap in capabilities:
        if isinstance(cap, dict):
            meta_tokens.append(str(cap.get("name", "")).lower())
            meta_tokens.append(str(cap.get("description", "")).lower())
            for item in cap.get("consumes", []):
                meta_tokens.append(str(item).lower())
            for item in cap.get("outputs", []):
                meta_tokens.append(str(item).lower())
            for item in cap.get("used_by", []):
                meta_tokens.append(str(item).lower())
    return " ".join(meta_tokens)


def _score_provider_relevance(provider: Any, search_query: str) -> float:
    """
    Implementation-agnostic capability matcher.
    Evaluates query intent against provider metadata (key, name, get_capabilities()).
    Returns relevance score >= 0.0.
    """
    q_str = str(search_query or "").strip().lower()
    if not q_str:
        return 1.0  # Return all when no query specified

    full_meta_text = _build_meta_text(provider)

    # Tokenize query, stripping common noise & meta-intent words
    stop_words = {
        "the", "a", "an", "and", "or", "in", "of", "to", "my", "me", "is", "for", "with", "across",
        "current", "highlight", "analyze", "analysis", "breakdown", "overview", "details", "summary",
        "report", "data", "list", "show", "get", "view"
    }
    raw_terms = [t.strip(",.?!;:()\"'") for t in q_str.split()]
    # len > 3, not > 1: short common words ("hi", "who", "fee") were matching
    # as substrings almost anywhere in provider metadata (e.g. "hi" inside
    # "achieve", "history"). Longer terms still match as substrings on
    # purpose, to catch plurals/stems ("certificate" in "certificates").
    query_terms = [t for t in raw_terms if len(t) > 3 and t not in stop_words]

    if not query_terms:
        return 1.0

    score = 0.0
    for term in query_terms:
        if term in full_meta_text:
            score += 1.0
            # Higher weight if matching provider key or name directly
            if term in provider.key.lower() or term in provider.name.lower():
                score += 2.0

    # Semantic synonym / concept bridge (e.g. deposit -> balance, property -> asset)
    synonym_map = {
        "deposit": ["balance", "cash", "account", "bank"],
        "liquidity": ["balance", "cash", "certificates"],
        "property": ["estate", "asset", "fixed"],
        "yield": ["certificate", "interest", "opportunity"],
        "income": ["salary", "interest", "expense"],
        "cost": ["expense", "spending"],
        "forex": ["market", "exchange", "currency"],
        "gold": ["fixed_assets", "market_data", "gold"],
    }
    for term in query_terms:
        for syn_key, targets in synonym_map.items():
            if syn_key in term:
                for tgt in targets:
                    if tgt in provider.key.lower() or tgt in full_meta_text:
                        score += 1.5

    return score


def get_relevant_providers_data(
    user: Any,
    search_query: str = "",
    limit: int | None = None,
    require_signal: bool = False,
) -> dict[str, Any]:
    """
    Dynamically queries relevant data providers matching the user's intent or search query.
    Performs capability metadata matching across all registered providers without hardcoded enums.

    require_signal: when True, returns an empty dict instead of falling back to
    ALL registered providers when no query term scores a positive match. Used for
    automatic/deterministic context injection (every chat turn) where silently
    dumping the entire business dataset for an unrelated query would be wasteful
    and noisy. The explicit query_application_data tool keeps the old "broad scan"
    fallback behavior (require_signal=False) since a model-initiated tool call is
    already an explicit signal that some data is wanted.
    """
    from core.services.ai.providers.registry import _DATA_PROVIDER_REGISTRY, autodiscover_providers

    if not _DATA_PROVIDER_REGISTRY:
        autodiscover_providers()

    query_str = str(search_query or "").strip()
    scores: dict[str, float] = {}

    for key, provider in _DATA_PROVIDER_REGISTRY.items():
        try:
            scores[key] = _score_provider_relevance(provider, query_str)
        except Exception as exc:
            logger.warning("Error scoring provider '%s': %s", key, exc)
            scores[key] = 1.0

    if query_str:
        apply_semantic_bonus(scores, _DATA_PROVIDER_REGISTRY, query_str, _build_meta_text)

    # Filter out weak trailing noise scores relative to top-scoring provider
    positive_scores = [s for s in scores.values() if s > 0.0]
    max_score = max(positive_scores) if positive_scores else 0.0

    if max_score >= 3.0:
        rel_threshold = max(3.0, max_score * 0.60)
        selected_keys = [k for k, s in scores.items() if scores[k] >= rel_threshold]
    elif positive_scores:
        selected_keys = [k for k, s in scores.items() if scores[k] > 0.0]
    elif require_signal:
        selected_keys = []
    else:
        selected_keys = list(_DATA_PROVIDER_REGISTRY.keys())

    res: dict[str, Any] = {}
    for key in selected_keys:
        provider = _DATA_PROVIDER_REGISTRY.get(key)
        if provider:
            try:
                res[provider.key] = provider.get_data(user, limit=limit)
            except Exception as exc:
                res[f"{provider.key}_error"] = str(exc)

    res["_explanation_metadata"] = {
        "search_query": query_str,
        "intent_matched": bool(query_str and positive_scores),
        "matched_providers": selected_keys,
        "total_providers_registered": len(_DATA_PROVIDER_REGISTRY),
        "skipped_providers": [k for k in _DATA_PROVIDER_REGISTRY.keys() if k not in selected_keys],
    }

    return res


def get_all_providers_data(user: Any, focus_area: str = "", limit: int | None = None) -> dict[str, Any]:
    """
    Queries data providers for user. Delegates to get_relevant_providers_data for intent-driven retrieval.
    """
    return get_relevant_providers_data(user, search_query=focus_area, limit=limit)
