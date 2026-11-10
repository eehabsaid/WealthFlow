"""Pack interface: how a host project plugs its own domain (tools, data providers, actions...) into ai/.

settings.AI_PACKS = ["myproject.ai_pack"]; each pack is a package with a ``pack`` module exposing
``register(registry)``. Without packs ai/ runs with its generic features only. See ai/INSTALL.md.
"""
import importlib
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class PackRegistry:
    """What packs may add. Every field has an empty default so ai/ never needs a pack."""

    def __init__(self):
        self.provider_packages: list[str] = []      # packages scanned for BaseContextProvider subclasses
        self.tool_defs: dict = {}                   # extra AI_TOOL_REGISTRY entries
        self.action_handlers: dict = {}             # record name -> module with propose/execute (confirm cards)
        self.action_records: list[str] = []         # record names the model may propose through propose_action
        self.param_validators: list = []            # fn(tool_name, params, timestamp) -> (audit, response) | None
        self.business_validators: list = []         # same signature, run after the auth checks (Rule 5)
        self.training_families: dict = {}           # family name -> module with train(user, langs, rng) / evaluate(...)
        self.url_modules: list[str] = []            # modules exposing urlpatterns
        self.data_enrichers: list = []              # fn(result, user, query, ctx) for the data-lookup tool
        self.agents: dict = {}                      # name -> agent class for the orchestrator
        self.ext: dict = {}                         # named single hooks (advisor, data_slice, insights, ...)

    def add_extension(self, name, obj):
        self.ext[name] = obj


_REGISTRY = PackRegistry()
_LOADED: list[str] = []


def registry() -> PackRegistry:
    return _REGISTRY


def ext(name, default=None):
    return _REGISTRY.ext.get(name, default)


def load_packs() -> list[str]:
    """Import every pack named in settings.AI_PACKS once and let it register itself."""
    for path in getattr(settings, "AI_PACKS", []):
        if path in _LOADED:
            continue
        try:
            importlib.import_module(f"{path}.pack").register(_REGISTRY)
            _LOADED.append(path)
        except Exception:
            logger.exception("AI pack %s failed to load", path)
    if _LOADED:
        from ai.services.tools.defs import AI_TOOL_REGISTRY
        AI_TOOL_REGISTRY.update({k: v for k, v in _REGISTRY.tool_defs.items() if k not in AI_TOOL_REGISTRY})
    return list(_LOADED)


def url_patterns() -> list:
    patterns = []
    for mod in _REGISTRY.url_modules:
        patterns += importlib.import_module(mod).urlpatterns
    return patterns


def advisor_services() -> list:
    """Advisor service keys the host can answer from (ext "advisor" = object with available() and payload())."""
    adv = ext("advisor")
    return list(adv.available()) if adv else []


def advisor_payload(key, user):
    adv = ext("advisor")
    return adv.payload(key, user) if adv else {}
