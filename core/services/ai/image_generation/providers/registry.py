"""Provider registry. A provider registers itself under a key; the saved `image_gen_provider` setting picks one.

Adding a provider = one new module with a class that subclasses ImageProvider and is decorated with @register.
Nothing else in the app names a provider.
"""

from __future__ import annotations

from .base import ImageProvider

_REGISTRY: dict[str, type[ImageProvider]] = {}


def register(cls: type[ImageProvider]) -> type[ImageProvider]:
    _REGISTRY[cls.key] = cls
    return cls


def get_provider_class(key: str) -> type[ImageProvider] | None:
    return _REGISTRY.get(str(key or "").strip().lower())


def provider_catalog() -> list[dict]:
    """What the settings page needs to draw its provider list and which fields each provider requires."""
    return [{"key": c.key, "label": c.label, "requires_endpoint": c.requires_endpoint, "requires_api_key": c.requires_api_key,
             "supports_edit": c.supports_edit} for c in _REGISTRY.values()]
