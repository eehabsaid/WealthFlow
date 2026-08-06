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


ALIAS_MAP = {
    "gold": ["market_data", "fixed_assets"],
    "gold_price": ["market_data"],
    "exchange_rates": ["market_data"],
    "certificates": ["bank_certificates"],
    "certificate": ["bank_certificates"],
    "cash": ["balances"],
    "balance": ["balances"],
    "assets": ["fixed_assets"],
    "asset": ["fixed_assets"],
    "advisor": ["financial_advisor"],
    "health": ["financial_advisor"],
    "income": ["salary"],
}


def get_all_providers_data(user: Any, focus_area: str = "", limit: int = 20) -> dict[str, Any]:
    """
    Query auto-discovered providers safely.
    Supports comma-separated focus_area strings and key aliases (e.g. 'gold, certificates').
    If focus_area is 'all', empty, or ambiguous, queries all registered providers.
    """
    if not _DATA_PROVIDER_REGISTRY:
        autodiscover_providers()

    clean_focus = str(focus_area or "").strip().lower()
    res: dict[str, Any] = {}

    if not clean_focus or clean_focus == "all":
        target_keys = set(_DATA_PROVIDER_REGISTRY.keys())
    else:
        parts = [p.strip() for p in clean_focus.replace(";", ",").split(",") if p.strip()]
        target_keys = set()
        for p in parts:
            if p in _DATA_PROVIDER_REGISTRY:
                target_keys.add(p)
            elif p in ALIAS_MAP:
                target_keys.update(ALIAS_MAP[p])

        if not target_keys:
            target_keys = set(_DATA_PROVIDER_REGISTRY.keys())

    for key in target_keys:
        provider = _DATA_PROVIDER_REGISTRY.get(key)
        if provider:
            try:
                res[provider.key] = provider.get_data(user, limit=limit)
            except Exception as exc:
                res[f"{provider.key}_error"] = str(exc)

    return res
