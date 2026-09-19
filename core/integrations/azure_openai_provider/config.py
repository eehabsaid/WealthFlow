"""
Config schema, from_settings construction, and capabilities for
AzureOpenAIProvider.

Split out of the former monolithic azure_openai_provider.py (200-line
rule). Kept separate from __init__.py since these methods never call
make_json_http_request — only __init__.py needs that import for the
existing @patch("core.integrations.azure_openai_provider.make_json_http_request")
test paths to keep resolving.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.services.ai.credential_encryption import decrypt_credential

if TYPE_CHECKING:
    from core.integrations.azure_openai_provider import AzureOpenAIProvider


class AzureOpenAIConfigMixin:
    @classmethod
    def from_settings(cls, user=None) -> Optional["AzureOpenAIProvider"]:
        from core.models import AppSettings

        raw_key = AppSettings.get("ai_azure_api_key", "", user=user).strip()
        api_key = decrypt_credential(raw_key)
        endpoint = AppSettings.get("ai_azure_endpoint", "", user=user).strip()
        deployment = AppSettings.get("ai_azure_deployment", "", user=user).strip()
        api_version = AppSettings.get("ai_azure_api_version", "2024-06-01", user=user).strip()
        try:
            timeout = int(AppSettings.get("ai_timeout", "60", user=user))
        except (ValueError, TypeError):
            timeout = 60

        return cls(
            api_key=api_key,
            endpoint=endpoint,
            deployment=deployment,
            api_version=api_version,
            timeout=timeout,
        )

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        return {
            "key": cls.PROVIDER_NAME,
            "label_key": "ai_provider_azure",
            "capabilities": {
                "supports_tools": True,
                "max_context_tokens": 128000,
            },
            "fields": [
                {
                    "name": "ai_azure_api_key",
                    "type": "password",
                    "is_secret": True,
                    "label_key": "ai_azure_api_key",
                    "required": False,
                },
                {
                    "name": "ai_azure_endpoint",
                    "type": "text",
                    "is_secret": False,
                    "label_key": "ai_azure_endpoint",
                    "placeholder": "https://your-resource.openai.azure.com",
                    "required": False,
                },
                {
                    "name": "ai_azure_deployment",
                    "type": "text",
                    "is_secret": False,
                    "label_key": "ai_azure_deployment",
                    "placeholder": "e.g. gpt-4o-deployment",
                    "required": False,
                },
                {
                    "name": "ai_azure_api_version",
                    "type": "text",
                    "is_secret": False,
                    "label_key": "ai_azure_api_version",
                    "placeholder": "2024-06-01",
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
