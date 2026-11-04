"""Image generation providers. Importing this package registers every built-in provider."""

from .base import ImageProvider, ImageProviderError, ImageResult, SourceImage
from .comfyui import ComfyUIProvider
from .registry import get_provider_class, provider_catalog, register

__all__ = ["ComfyUIProvider", "ImageProvider", "ImageProviderError", "ImageResult", "SourceImage", "get_provider_class", "provider_catalog", "register"]
