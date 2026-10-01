"""Capability registry: the query engine's view of the existing provider registry.

Each BaseContextProvider declares what it can answer once, in get_query_capabilities().
This module only *collects* those declarations (no parallel registry), caches them, and
describes them to CapabilityRegistry / the LLM slot-filling prompt.
"""

from __future__ import annotations

import logging
from typing import Any

from .spec import Capability

logger = logging.getLogger(__name__)
_CACHE: list[Capability] | None = None


def get_capabilities() -> list[Capability]:
    global _CACHE
    if _CACHE is None:
        from core.services.ai.providers.registry import DATA_PROVIDER_REGISTRY, autodiscover_providers

        providers = DATA_PROVIDER_REGISTRY or autodiscover_providers()
        caps: list[Capability] = []
        for key, provider in providers.items():
            try:
                caps.extend(provider.get_query_capabilities())
            except Exception as exc:  # a broken provider must never break chat
                logger.warning("query capabilities of provider %r failed: %s", key, exc)
        _CACHE = caps
    return _CACHE


def get_capability(key: str) -> Capability | None:
    return next((c for c in get_capabilities() if c.key == key), None)


def reset_cache() -> None:
    global _CACHE
    _CACHE = None


def describe_capabilities() -> list[dict[str, Any]]:
    """Entries for CapabilityRegistry.autodiscover() (same dict shape as provider capabilities)."""
    return [{
        "name": f"Instant answer: {c.label}", "provided_by": c.provider_key,
        "consumes": list(c.sources), "used_by": ["AI Chat query engine"],
        "inputs": ["metric", "group_by", "period", *c.filters],
        "outputs": c.metric_names(),
        "description": f"Answered by code with 0 LLM calls. metrics={c.metric_names()} group_by={c.dimension_names()} "
                       f"filters={list(c.filters)} time={c.time}.",
    } for c in get_capabilities()]


def catalogue_for_prompt() -> str:
    """Compact capability catalogue for the one-shot LLM slot-filling call (~150 tokens)."""
    return "\n".join(
        f"{c.key}: metrics={'|'.join(c.metric_names())}; group_by={'|'.join(c.dimension_names()) or '-'}; "
        f"filters={','.join(c.filters) or '-'}; time={c.time}" for c in get_capabilities()
    )
