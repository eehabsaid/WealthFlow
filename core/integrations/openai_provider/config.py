"""
Config schema, from_settings construction, and capabilities for
OpenAIProvider.

Split out of the former monolithic openai_provider.py (200-line rule).
Kept separate from __init__.py since these methods never call
make_json_http_request — only __init__.py needs that import for the
existing @patch("core.integrations.openai_provider.make_json_http_request")
test paths to keep resolving.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.services.ai.credential_encryption import decrypt_credential

if TYPE_CHECKING:
    from core.integrations.openai_provider import OpenAIProvider


class OpenAIConfigMixin:
    @classmethod
    def from_settings(cls, user=None) -> Optional["OpenAIProvider"]:
        from core.models import AppSettings

        raw_key = AppSettings.get("ai_openai_api_key", "", user=user).strip()
        api_key = decrypt_credential(raw_key)
        model = AppSettings.get("ai_openai_model", "", user=user).strip()
        base_url = AppSettings.get("ai_openai_base_url", "https://api.openai.com/v1", user=user).strip()
        try:
            timeout = int(AppSettings.get("ai_timeout", "60", user=user))
        except (ValueError, TypeError):
            timeout = 60

        return cls(api_key=api_key, model=model, base_url=base_url, timeout=timeout)

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        return {
            "key": cls.PROVIDER_NAME,
            "label_key": "ai_provider_openai",
            "capabilities": {
                "supports_tools": True,
                "max_context_tokens": 128000,
            },
            "fields": [
                {
                    "name": "ai_openai_api_key",
                    "type": "password",
                    "is_secret": True,
                    "label_key": "ai_openai_api_key",
                    "required": False,
                },
                {
                    "name": "ai_openai_model",
                    "type": "text",
                    "is_secret": False,
                    "label_key": "ai_model",
                    "placeholder": "e.g. gpt-4o, gpt-4o-mini",
                    "required": False,
                },
                {
                    "name": "ai_openai_base_url",
                    "type": "text",
                    "is_secret": False,
                    "label_key": "ai_base_url",
                    "placeholder": "https://api.openai.com/v1",
                    "required": False,
                },
            ],
        }

    @property
    def capabilities(self) -> dict[str, Any]:
        return {
            "supports_tools": self.supports_tools,
            "max_context_tokens": 128000,
        }
