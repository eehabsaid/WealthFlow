"""generate_image: the one entry point the AI tool (and the settings test) use. Provider-independent."""

from __future__ import annotations

import logging

from ai.services.image_generation.providers import ImageProviderError, get_provider_class
from ai.services.image_generation.providers.base import SourceImage
from ai.services.image_generation.settings import get_image_config, image_generation_available
from ai.services.image_generation.storage import inspect_image, resolve_source, save_generated

logger = logging.getLogger(__name__)

TIMEOUT_S = 300
SIZE_MIN, SIZE_MAX, SIZE_STEP, SIZE_DEFAULT = 256, 2048, 16, 1024


def clamp_size(value, fallback: int = SIZE_DEFAULT) -> int:
    try:
        n = int(float(str(value)))
    except (TypeError, ValueError):
        n = fallback
    return max(SIZE_MIN, min(SIZE_MAX, n // SIZE_STEP * SIZE_STEP))


def build_provider(overrides: dict | None = None):
    """The provider selected in the settings (optionally with unsaved form values, for the Test button)."""
    cfg = {**get_image_config(include_secret=True), **{k: v for k, v in (overrides or {}).items() if v is not None and (v != "" or k == "start_command")}}
    cls = get_provider_class(cfg.get("provider", ""))
    if cls is None:
        raise ImageProviderError("No image generation provider is selected.")
    return cls(cfg, TIMEOUT_S)


def test_connection(overrides: dict | None = None) -> str:
    return build_provider(overrides).test_connection()


def _size_for(source: SourceImage | None, params: dict) -> tuple[int, int]:
    width, height = params.get("width"), params.get("height")
    if source is not None and not (width and height):   # keep the picture's proportions when editing
        try:
            w, h = inspect_image(source.data)[2]
            scale = SIZE_DEFAULT / max(w, h)
            return clamp_size(w * scale), clamp_size(h * scale)
        except ImageProviderError:
            pass
    return clamp_size(width), clamp_size(height)


def generate_image(user, params: dict) -> dict:
    """Tool handler. Never raises: a disabled feature or an unavailable provider is a plain error the model can relay."""
    prompt = str(params.get("prompt") or "").strip()
    if not prompt:
        return {"error": "`prompt` is required"}
    if not image_generation_available():
        return {"error": "Image generation is switched off or not configured. Tell the user to ask an administrator to enable it in Settings > AI Advisor."}
    try:
        provider = build_provider()
        source = resolve_source(user, params.get("source_image_id"), bool(params.get("use_previous")))
        if source is not None and not provider.supports_edit:
            return {"error": "The configured image provider cannot edit images."}
        width, height = _size_for(source, params)
        result = provider.generate(prompt, width=width, height=height, source=source)
        attachment = save_generated(user, result.data, prompt)
    except ImageProviderError as exc:
        return {"error": f"Image generation failed: {exc}"}
    except Exception:
        logger.exception("Image generation failed unexpectedly")
        return {"error": "Image generation failed; the image provider is unavailable right now."}
    return {"ok": True, "image_id": attachment.id, "edited": source is not None,
            "note": "The app shows the image under your answer with a download button. Do NOT write a link, path or file name. "
                    "Tell the user in one or two sentences what the image shows."}
