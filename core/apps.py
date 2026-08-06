from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self) -> None:
        """Autodiscover AI context providers, capabilities, and validate tool registry at startup."""
        try:
            from core.services.ai.providers.registry import autodiscover_providers
            from core.services.ai.capability_registry import CapabilityRegistry
            from core.services.ai.tools_registry import validate_tool_registry

            autodiscover_providers()
            CapabilityRegistry.autodiscover()
            errs = validate_tool_registry()
            if errs:
                import logging
                logger = logging.getLogger(__name__)
                for err in errs:
                    logger.warning("AI Subsystem Startup Validation Warning: %s", err)
        except Exception:
            pass
