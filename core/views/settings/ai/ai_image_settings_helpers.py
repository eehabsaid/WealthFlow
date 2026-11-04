"""Image generation settings payload, validation and persistence for the AI settings page (same flow as the speech settings)."""

from core.services.ai.image_generation import get_image_config, provider_catalog, save_image_settings, validate_image_settings
from core.services.ai.image_generation.settings import FIELDS


def build_image_settings_payload():
    cfg = get_image_config()
    payload = {f"image_gen_{field}": cfg[field] for field in FIELDS}
    payload.update({"image_gen_configured": cfg["is_configured"], "image_gen_api_key_is_configured": cfg["api_key_is_configured"],
                    "image_gen_providers": provider_catalog()})
    return payload


def validate_image_settings_data(data):
    return validate_image_settings(data)


def persist_image_settings(data):
    save_image_settings(data)
