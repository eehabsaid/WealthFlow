from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AIConfig(AppConfig):
    name = "ai"
    label = "ai"

    def ready(self) -> None:
        """Register host packs, then autodiscover AI context providers and capabilities."""
        from ai.legacy import post_migrate_copy
        post_migrate.connect(post_migrate_copy, dispatch_uid="ai_legacy_settings_copy")
        try:
            from ai.packs import load_packs
            from ai.services.providers.registry import autodiscover_providers
            from ai.services.capability_registry import CapabilityRegistry

            load_packs()
            from ai.services.query_engine.registry import reset_cache

            autodiscover_providers()
            reset_cache()   # capabilities cached before the packs registered would be empty
            CapabilityRegistry.autodiscover()
        except Exception:
            pass
