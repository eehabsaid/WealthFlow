from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self) -> None:
        """Autodiscover AI context providers and capabilities at startup."""
        try:
            from core.services.ai.providers.registry import autodiscover_providers
            from core.services.ai.capability_registry import CapabilityRegistry

            autodiscover_providers()
            CapabilityRegistry.autodiscover()
        except Exception:
            pass
