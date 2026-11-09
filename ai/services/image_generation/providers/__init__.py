"""Image generation providers. Importing this package registers every built-in provider."""

from ai.services.image_generation.providers.base import (
    ImageProvider,
    ImageProviderError,
    ImageResult,
    SourceImage,
)
from ai.services.image_generation.providers.comfyui import ComfyUIProvider
from ai.services.image_generation.providers.registry import (
    get_provider_class,
    provider_catalog,
    register,
)

__all__ = ["ComfyUIProvider", "ImageProvider", "ImageProviderError", "ImageResult", "SourceImage", "get_provider_class", "provider_catalog", "register"]
