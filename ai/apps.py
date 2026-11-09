from django.apps import AppConfig


class AIConfig(AppConfig):
    name = "ai"
    label = "ai"

    def ready(self) -> None:
        """Autodiscover AI context providers and capabilities at startup."""
        try:
            from ai.services.providers.registry import autodiscover_providers
            from ai.services.capability_registry import CapabilityRegistry

            autodiscover_providers()
            CapabilityRegistry.autodiscover()
        except Exception:
            pass
