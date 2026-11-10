"""Configurable AI image generation: a provider-independent `generate_image` tool (text-to-image and image editing).

  settings.py    the five AISetting fields (enabled, provider, model, endpoint, api_key) and the availability check
  providers/     the provider interface, registry and the ComfyUI provider (workflow templates are JSON data files)
  service.py     generate_image(): provider call + saving; test_connection() for the settings page
  storage.py     images are stored as AIAttachment rows (owner-scoped) and linked to the answer that made them
  tool.py        the registry entry the AI agent loads
"""

from ai.services.image_generation.lifecycle import apply_settings_change, warm_start_if_enabled
from ai.services.image_generation.providers import provider_catalog
from ai.services.image_generation.service import generate_image, test_connection
from ai.services.image_generation.settings import (
    get_image_config,
    image_generation_available,
    save_image_settings,
    validate_image_settings,
)
from ai.services.image_generation.storage import attach_generated_images
from ai.services.image_generation.tool import NAME, NOTICE, TOOL_DEF

__all__ = ["NAME", "NOTICE", "TOOL_DEF", "apply_settings_change", "attach_generated_images", "warm_start_if_enabled", "generate_image", "get_image_config", "image_generation_available",
           "provider_catalog", "save_image_settings", "test_connection", "validate_image_settings"]
