"""
Automatic Provider Discovery & Registry for AI context subsystem.
Dynamically discovers all BaseContextProvider implementations in core.services.ai.providers at startup.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import logging
from typing import Any
from core.services.ai.providers.base import BaseContextProvider

logger = logging.getLogger(__name__)

_DATA_PROVIDER_REGISTRY: dict[str, BaseContextProvider] = {}


def autodiscover_providers() -> dict[str, BaseContextProvider]:
    """
    Dynamically scans core.services.ai.providers package for BaseContextProvider subclasses
    and registers them automatically without requiring manual registry edits.
    """
    _DATA_PROVIDER_REGISTRY.clear()

    import core.services.ai.providers as providers_pkg
    package_path = providers_pkg.__path__

    for _, module_name, _ in pkgutil.iter_modules(package_path):
        if module_name in ("base", "registry"):
            continue
        try:
            full_module_name = f"core.services.ai.providers.{module_name}"
            module = importlib.import_module(full_module_name)

            for _, cls in inspect.getmembers(module, inspect.isclass):
                if issubclass(cls, BaseContextProvider) and cls is not BaseContextProvider:
                    inst = cls()
                    if inst.key in _DATA_PROVIDER_REGISTRY:
                        logger.warning("Duplicate provider key '%s' discovered in %s", inst.key, full_module_name)
                    else:
                        _DATA_PROVIDER_REGISTRY[inst.key] = inst
        except Exception as exc:
            logger.error("Failed to autodiscover AI provider module '%s': %s", module_name, exc)

    return _DATA_PROVIDER_REGISTRY


# Initialize registry on load
autodiscover_providers()

DATA_PROVIDER_REGISTRY = _DATA_PROVIDER_REGISTRY


def get_data_provider(key: str) -> BaseContextProvider | None:
    """Lookup data provider by key."""
    if not _DATA_PROVIDER_REGISTRY:
        autodiscover_providers()
    return _DATA_PROVIDER_REGISTRY.get(str(key or "").strip().lower())


def _score_provider_relevance(provider: BaseContextProvider, search_query: str) -> float:
    """
    Implementation-agnostic capability matcher.
    Evaluates query intent against provider metadata (key, name, get_capabilities()).
    Returns relevance score >= 0.0.
    """
    q_str = str(search_query or "").strip().lower()
    if not q_str:
        return 1.0  # Return all when no query specified

    # Collect metadata fields into a unified capability text index
    meta_tokens: list[str] = [
        provider.key.lower(),
        provider.name.lower(),
    ]

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

    full_meta_text = " ".join(meta_tokens)

    # Tokenize query, stripping common noise words
    stop_words = {"the", "a", "an", "and", "or", "in", "of", "to", "my", "me", "is", "for", "with", "across", "current", "highlight"}
    raw_terms = [t.strip(",.?!;:()\"'") for t in q_str.split()]
    query_terms = [t for t in raw_terms if len(t) > 1 and t not in stop_words]

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


def get_relevant_providers_data(user: Any, search_query: str = "", limit: int = 20) -> dict[str, Any]:
    """
    Dynamically queries relevant data providers matching the user's intent or search query.
    Performs capability metadata matching across all registered providers without hardcoded enums.
    """
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

    # If any provider scored > 0, select only positive scoring providers; otherwise fallback to all
    positive_keys = [k for k, s in scores.items() if s > 0.0]
    selected_keys = positive_keys if (positive_keys and query_str) else list(_DATA_PROVIDER_REGISTRY.keys())

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
        "intent_matched": bool(query_str and positive_keys),
        "matched_providers": selected_keys,
        "total_providers_registered": len(_DATA_PROVIDER_REGISTRY),
        "skipped_providers": [k for k in _DATA_PROVIDER_REGISTRY.keys() if k not in selected_keys],
    }

    return res


def get_all_providers_data(user: Any, focus_area: str = "", limit: int = 20) -> dict[str, Any]:
    """
    Queries data providers for user. Delegates to get_relevant_providers_data for intent-driven retrieval.
    """
    return get_relevant_providers_data(user, search_query=focus_area, limit=limit)

