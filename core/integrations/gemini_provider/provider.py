"""
Gemini (Google Generative AI) Provider Implementation.

Interacts with Google's Generative Language REST API via stdlib urllib.request.
Supports system instructions, message conversion, function declarations, token usage, and secret redaction.
"""

from __future__ import annotations

import logging

from core.integrations.ai_provider import BaseAIProvider
from core.integrations.gemini_provider.config_mixin import GeminiConfigMixin
from core.integrations.gemini_provider.connection_mixin import GeminiConnectionMixin
from core.integrations.gemini_provider.request_mixin import GeminiRequestMixin

logger = logging.getLogger(__name__)


class GeminiProvider(GeminiConfigMixin, GeminiRequestMixin, GeminiConnectionMixin, BaseAIProvider):
    PROVIDER_NAME = "gemini"
    supports_tools: bool = True

    def __init__(
        self,
        api_key: str = "",
        model: str = "",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout: int = 15,
    ) -> None:
        self.api_key = api_key or ""
        self.model = model or ""
        self.base_url = (base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        self.timeout = max(1, int(timeout))
