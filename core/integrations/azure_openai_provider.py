"""
Azure OpenAI Provider Implementation.

Interacts with Azure OpenAI deployment endpoints via stdlib urllib.request.
Supports deployment-based completions, tool calling, token usage tracking, and secret redaction.
"""

from __future__ import annotations

import logging
import time
import urllib.parse
from typing import Any, Optional

from core.integrations.ai_provider import BaseAIProvider
from core.integrations.provider_utils import make_json_http_request
from core.services.ai.credential_encryption import (
    decrypt_credential,
    redact_secrets,
)

logger = logging.getLogger(__name__)


class AzureOpenAIProvider(BaseAIProvider):
    PROVIDER_NAME = "azure"
    supports_tools: bool = True

    def __init__(
        self,
        api_key: str = "",
        endpoint: str = "",
        deployment: str = "",
        api_version: str = "2024-06-01",
        timeout: int = 15,
    ) -> None:
        self.api_key = api_key or ""
        self.endpoint = (endpoint or "").rstrip("/")
        self.deployment = (deployment or "").strip()
        self.api_version = (api_version or "2024-06-01").strip()
        self.timeout = max(1, int(timeout))

    @classmethod
    def from_settings(cls) -> Optional[AzureOpenAIProvider]:
        from core.models import AppSettings

        raw_key = AppSettings.get("ai_azure_api_key", "").strip()
        api_key = decrypt_credential(raw_key)
        endpoint = AppSettings.get("ai_azure_endpoint", "").strip()
        deployment = AppSettings.get("ai_azure_deployment", "").strip()
        api_version = AppSettings.get("ai_azure_api_version", "2024-06-01").strip()
        try:
            timeout = int(AppSettings.get("ai_timeout", "15"))
        except (ValueError, TypeError):
            timeout = 15

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

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not self.api_key:
            err = "Azure OpenAI API key is unconfigured or missing."
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": err}

        if not self.endpoint or not self.deployment:
            err = "Azure OpenAI endpoint and deployment must be configured."
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": err}

        version_param = urllib.parse.quote(self.api_version)
        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={version_param}"

        headers = {
            "api-key": self.api_key,
        }
        payload: dict[str, Any] = {
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools

        secrets = [self.api_key]
        data, status, err = make_json_http_request(
            url=url,
            method="POST",
            headers=headers,
            payload=payload,
            timeout=self.timeout,
            secrets=secrets,
        )

        if err:
            safe_err = redact_secrets(err, secrets)
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": safe_err}

        if not isinstance(data, dict):
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": "Invalid response format from Azure OpenAI API."}

        choices = data.get("choices", [])
        msg = choices[0].get("message", {}) if isinstance(choices, list) and choices else {}
        content = str(msg.get("content", "") or "").strip()
        tool_calls = msg.get("tool_calls")

        usage = data.get("usage") or {}
        prompt_tokens = usage.get("prompt_tokens") if isinstance(usage, dict) else None
        completion_tokens = usage.get("completion_tokens") if isinstance(usage, dict) else None

        return {
            "content": content,
            "tool_calls": tool_calls,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "error": None,
        }

    def check_connection(self) -> dict[str, Any]:
        start = time.perf_counter()
        if not self.api_key or not self.endpoint:
            return {"reachable": False, "version": None, "error": "Azure OpenAI API key or endpoint is missing.", "response_time_ms": 0}

        secrets = [self.api_key]
        version_param = urllib.parse.quote(self.api_version)
        url = f"{self.endpoint}/openai/deployments?api-version={version_param}"
        headers = {"api-key": self.api_key}

        data, status, err = make_json_http_request(url=url, method="GET", headers=headers, timeout=self.timeout, secrets=secrets)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if err:
            safe_err = redact_secrets(err, secrets)
            return {"reachable": False, "version": None, "error": safe_err, "response_time_ms": elapsed_ms}

        return {"reachable": True, "version": self.api_version, "error": None, "response_time_ms": elapsed_ms}

    def list_models(self) -> list[dict[str, Any]]:
        if not self.api_key or not self.endpoint:
            if self.deployment:
                return [{"name": self.deployment, "model": self.deployment}]
            return []

        secrets = [self.api_key]
        version_param = urllib.parse.quote(self.api_version)
        url = f"{self.endpoint}/openai/deployments?api-version={version_param}"
        headers = {"api-key": self.api_key}

        data, status, err = make_json_http_request(url=url, method="GET", headers=headers, timeout=self.timeout, secrets=secrets)
        if err or not isinstance(data, dict):
            if self.deployment:
                return [{"name": self.deployment, "model": self.deployment}]
            return []

        data_list = data.get("data", [])
        if isinstance(data_list, list) and data_list:
            res = []
            for item in data_list:
                if isinstance(item, dict):
                    did = str(item.get("id", "")).strip()
                    if did:
                        res.append({"name": did, "model": did})
            return res or ([{"name": self.deployment, "model": self.deployment}] if self.deployment else [])

        if self.deployment:
            return [{"name": self.deployment, "model": self.deployment}]
        return []

    def check_model_available(self, model: str) -> bool:
        target = (model or self.deployment or "").strip().lower()
        if not target:
            return False
        return bool(self.api_key and self.endpoint)
