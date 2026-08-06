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


def get_all_providers_data(user: Any, focus_area: str = "", limit: int = 20) -> dict[str, Any]:
    """
    Queries all auto-discovered data providers, providing complete, un-truncated
    cross-module business context (Salary, Balances, Expenses, Fixed Assets, Certificates, Market Data, Advisor)
    for semantic LLM reasoning.
    """
    if not _DATA_PROVIDER_REGISTRY:
        autodiscover_providers()

    res: dict[str, Any] = {}
    for key, provider in _DATA_PROVIDER_REGISTRY.items():
        try:
            res[provider.key] = provider.get_data(user, limit=limit)
        except Exception as exc:
            res[f"{provider.key}_error"] = str(exc)

    return res
