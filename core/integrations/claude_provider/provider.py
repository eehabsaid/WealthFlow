"""
Claude (Anthropic) Provider Implementation.

Interacts with Anthropic's Messages API (/v1/messages) via stdlib urllib.request.
Converts system prompts, messages, tool schemas, token usage tracking, and secret redaction.
"""

from __future__ import annotations

import logging

from core.integrations.ai_provider import BaseAIProvider
from core.integrations.claude_provider.config_mixin import ClaudeConfigMixin
from core.integrations.claude_provider.connection_mixin import ClaudeConnectionMixin
from core.integrations.claude_provider.request_mixin import ClaudeRequestMixin

logger = logging.getLogger(__name__)


class ClaudeProvider(ClaudeConfigMixin, ClaudeRequestMixin, ClaudeConnectionMixin, BaseAIProvider):
    PROVIDER_NAME = "claude"
    supports_tools: bool = True

    def __init__(
        self,
        api_key: str = "",
        model: str = "",
        base_url: str = "https://api.anthropic.com/v1",
        timeout: int = 15,
    ) -> None:
        self.api_key = api_key or ""
        self.model = model or ""
        self.base_url = (base_url or "https://api.anthropic.com/v1").rstrip("/")
        self.timeout = max(1, int(timeout))
