"""The provider-independent image generation interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ImageProviderError(Exception):
    """A provider failure with a short, user-safe message (never a stack trace or a secret)."""


@dataclass(frozen=True)
class SourceImage:
    data: bytes
    name: str
    mime: str


@dataclass(frozen=True)
class ImageResult:
    data: bytes


class ImageProvider(ABC):
    key = ""
    label = ""
    requires_endpoint = True
    requires_api_key = False
    supports_edit = True
    supports_managed_server = False   # True: the provider's server can be started / stopped by WealthFlow (start_command setting)

    def __init__(self, cfg: dict, timeout: int):
        self.cfg = cfg                      # {model, endpoint, api_key, ...} exactly as saved in the settings
        self.timeout = timeout

    def prepare(self) -> str:
        """Called before every generation / test: bring the provider's server up if WealthFlow manages it. Returns a status note."""
        return ""

    def warm_start(self) -> None:
        """Start the managed server in the background (no-op for providers without one)."""

    def shutdown(self) -> None:
        """Stop the managed server WealthFlow started (no-op for providers without one)."""

    @abstractmethod
    def test_connection(self) -> str:
        """Short success text; raises ImageProviderError when the provider cannot be used with these settings."""

    @abstractmethod
    def generate(self, prompt: str, *, width: int, height: int, source: SourceImage | None = None) -> ImageResult:
        """Text-to-image (source is None) or image-to-image editing. Raises ImageProviderError on any failure."""
