"""
Settings/config-schema loading and reported capabilities for ClaudeProvider.
"""

from __future__ import annotations

from typing import Any, Optional

from core.services.ai.credential_encryption import decrypt_credential


class ClaudeConfigMixin:
    @classmethod
    def from_settings(cls) -> Optional["ClaudeConfigMixin"]:
        from core.models import AppSettings

        raw_key = AppSettings.get("ai_claude_api_key", "").strip()
        api_key = decrypt_credential(raw_key)
        model = AppSettings.get("ai_claude_model", "").strip()
        base_url = AppSettings.get("ai_claude_base_url", "https://api.anthropic.com/v1").strip()
        try:
            timeout = int(AppSettings.get("ai_timeout", "60"))
        except (ValueError, TypeError):
            timeout = 60

        return cls(api_key=api_key, model=model, base_url=base_url, timeout=timeout)

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        return {
            "key": cls.PROVIDER_NAME,
            "label_key": "ai_provider_claude",
            "capabilities": {
                "supports_tools": True,
                "max_context_tokens": 200000,
            },
            "fields": [
                {
                    "name": "ai_claude_api_key",
                    "type": "password",
                    "is_secret": True,
                    "label_key": "ai_claude_api_key",
                    "required": False,
                },
                {
                    "name": "ai_claude_model",
                    "type": "text",
                    "is_secret": False,
                    "label_key": "ai_model",
                    "placeholder": "e.g. claude-3-5-sonnet-20241022",
                    "required": False,
                },
            ],
        }

    @property
    def capabilities(self) -> dict[str, Any]:
        return {
            "supports_tools": self.supports_tools,
            "max_context_tokens": 200000,
        }
