"""
OpenAI Provider Implementation.

Interacts with OpenAI's Chat Completions API (/v1/chat/completions) via stdlib urllib.request.
Supports function/tool calling, model listing, token usage tracking, and secret redaction.

Split into a package (200-line rule):
  - config.py : OpenAIConfigMixin (from_settings, get_config_schema, capabilities)
  - __init__.py (this file) : OpenAIProvider class with __init__, generate,
    check_connection, list_models, check_model_available — kept together
    here (not in config.py) because these call make_json_http_request,
    imported at module level right below, and existing tests patch
    "core.integrations.openai_provider.make_json_http_request" — that
    patch only takes effect on calls made from code defined in this
    module's own namespace.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from core.integrations.ai_provider import BaseAIProvider
from core.integrations.provider_utils import make_json_http_request
from core.integrations.openai_provider.config import OpenAIConfigMixin
from core.services.ai.credential_encryption import redact_secrets


logger = logging.getLogger(__name__)


class OpenAIProvider(OpenAIConfigMixin, BaseAIProvider):
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
