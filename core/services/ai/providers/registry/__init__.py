"""
Automatic Provider Discovery & Registry for AI context subsystem.
Dynamically discovers all BaseContextProvider implementations in core.services.ai.providers at startup.

Split into a package (200-line rule):
  - __init__.py (this file) : registry dict, autodiscover_providers,
    get_data_provider — kept together since autodiscover_providers()
    is invoked once at package-import time to populate the shared
    _DATA_PROVIDER_REGISTRY dict.
  - scoring.py : _score_provider_relevance, get_relevant_providers_data,
    get_all_providers_data — imports the registry dict back from this
    __init__.py lazily (inside the function body) to avoid a circular
    import at load time.

pkgutil.iter_modules() on the parent core.services.ai.providers package
still sees this subpackage as a module named "registry" (same name as
before), so the existing `if module_name in ("base", "registry"):
continue` skip in autodiscover_providers() below is unaffected.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import logging
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


from core.services.ai.providers.registry.scoring import (  # noqa: E402
    get_relevant_providers_data,
    get_all_providers_data,
)

__all__ = [
    "DATA_PROVIDER_REGISTRY",
    "autodiscover_providers",
    "get_data_provider",
    "get_relevant_providers_data",
    "get_all_providers_data",
]
