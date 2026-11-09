"""When WealthFlow starts and stops the image server (the provider decides how; nothing here names a provider)."""

from __future__ import annotations

import logging

from ai.services.image_generation.providers import get_provider_class
from ai.services.image_generation.service import build_provider
from ai.services.image_generation.settings import get_image_config, image_generation_available

logger = logging.getLogger(__name__)


def warm_start_if_enabled() -> None:
    """Image generation is enabled and configured: bring the provider's server up in the background (cheap if it already runs)."""
    try:
        if image_generation_available():
            build_provider().warm_start()
    except Exception:
        logger.exception("Image server warm start could not be scheduled")


def apply_settings_change() -> None:
    """After the image settings were saved: enabled -> start the server; switched off -> stop the one WealthFlow started."""
    try:
        if image_generation_available():
            build_provider().warm_start()
            return
        cfg = get_image_config(include_secret=True)
        cls = get_provider_class(cfg["provider"])
        if cls is not None and cls.supports_managed_server:
            cls(cfg, 0).shutdown()
    except Exception:
        logger.exception("Image server could not be started or stopped after a settings change")
