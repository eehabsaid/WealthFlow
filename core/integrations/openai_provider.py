"""
OpenAI Provider Implementation.

Interacts with OpenAI's Chat Completions API (/v1/chat/completions) via stdlib urllib.request.
Supports function/tool calling, model listing, token usage tracking, and secret redaction.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from core.integrations.ai_provider import BaseAIProvider
from core.integrations.provider_utils import make_json_http_request
from core.services.ai.credential_encryption import (
    decrypt_credential,
    redact_secrets,
)


logger = logging.getLogger(__name__)


class OpenAIProvider(BaseAIProvider):
    PROVIDER_NAME = "openai"
    supports_tools: bool = True

    def __init__(
        self,
        api_key: str = "",
        model: str = "",
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 15,
    ) -> None:
        self.api_key = api_key or ""
        self.model = model or ""
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.timeout = max(1, int(timeout))

    @classmethod
    def from_settings(cls) -> Optional[OpenAIProvider]:
        from core.models import AppSettings

        raw_key = AppSettings.get("ai_openai_api_key", "").strip()
        api_key = decrypt_credential(raw_key)
        model = AppSettings.get("ai_openai_model", "").strip()
        base_url = AppSettings.get("ai_openai_base_url", "https://api.openai.com/v1").strip()
        try:
            timeout = int(AppSettings.get("ai_timeout", "60"))
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

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not self.api_key:
            err = "OpenAI API key is unconfigured or missing."
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": err}

        model_name = str(kwargs.get("model") or self.model or "").strip()
        if not model_name:
            err = "OpenAI model name is unconfigured."
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": err}

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        payload: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools

        secrets = [self.api_key]
        timeout = int(kwargs.get("timeout") or max(self.timeout, 120))
        data, status, err = make_json_http_request(
            url=url,
            method="POST",
            headers=headers,
            payload=payload,
            timeout=timeout,
            secrets=secrets,
        )

        if err:
            safe_err = redact_secrets(err, secrets)
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": safe_err}

        if not isinstance(data, dict):
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": "Invalid response format from OpenAI API."}

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
        if not self.api_key:
            return {"reachable": False, "version": None, "error": "OpenAI API key is missing.", "response_time_ms": 0}

        secrets = [self.api_key]
        url = f"{self.base_url}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        data, status, err = make_json_http_request(url=url, method="GET", headers=headers, timeout=self.timeout, secrets=secrets)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if err:
            safe_err = redact_secrets(err, secrets)
            return {"reachable": False, "version": None, "error": safe_err, "response_time_ms": elapsed_ms}

        return {"reachable": True, "version": "v1", "error": None, "response_time_ms": elapsed_ms}

    def list_models(self) -> list[dict[str, Any]]:
        if not self.api_key:
            return []
        secrets = [self.api_key]
        url = f"{self.base_url}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        data, status, err = make_json_http_request(url=url, method="GET", headers=headers, timeout=self.timeout, secrets=secrets)
        if err or not isinstance(data, dict):
            return []

        data_list = data.get("data", [])
        if isinstance(data_list, list):
            res = []
            for item in data_list:
                if isinstance(item, dict):
                    mid = str(item.get("id", "")).strip()
                    if mid:
                        res.append({"name": mid, "model": mid})
            return res
        return []

    def check_model_available(self, model: str) -> bool:
        target = (model or self.model or "").strip().lower()
        if not target:
            return False
        models = self.list_models()
        if not models:
            # If list_models is blocked or empty, accept requested model format defensively
            return bool(target)
        for m in models:
            if str(m.get("name", "")).strip().lower() == target:
                return True
        return False
