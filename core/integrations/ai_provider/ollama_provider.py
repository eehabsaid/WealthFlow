"""Ollama implementation of BaseAIProvider."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from core.integrations.provider_utils import make_json_http_request
from core.services.ai.ai_defaults import DEFAULT_OLLAMA_MODEL
from core.services.ai.credential_encryption import redact_secrets

from .base import BaseAIProvider
from .ollama_connection_mixin import OllamaConnectionMixin

logger = logging.getLogger(__name__)


class OllamaProvider(OllamaConnectionMixin, BaseAIProvider):
    """
    Ollama implementation of BaseAIProvider.
    Interacts with Ollama's HTTP API (/api/version, /api/tags, /api/chat).
    """

    PROVIDER_NAME = "ollama"
    supports_tools: bool = True

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "",
        timeout: int = 15,
        user_agent: str = "WealthFlow/1.0",
    ) -> None:
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")
        self.model = model or ""
        self.timeout = max(1, int(timeout))
        self.user_agent = user_agent

    @classmethod
    def from_settings(cls) -> Optional["OllamaProvider"]:
        from core.models import AppSettings

        base_url = AppSettings.get("ai_ollama_url", "http://localhost:11434").strip()
        model = AppSettings.get("ai_model", DEFAULT_OLLAMA_MODEL).strip()
        try:
            timeout = int(AppSettings.get("ai_timeout", "60"))
        except (ValueError, TypeError):
            timeout = 60

        return cls(base_url=base_url, model=model, timeout=timeout)

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        return {
            "key": cls.PROVIDER_NAME,
            "label_key": "ai_provider_ollama",
            "capabilities": {
                "supports_tools": True,
                "max_context_tokens": None,
            },
            "fields": [
                {
                    "name": "ai_ollama_url",
                    "type": "url",
                    "is_secret": False,
                    "label_key": "ai_ollama_url",
                    "placeholder": "http://localhost:11434",
                    "required": False,
                },
                {
                    "name": "ai_model",
                    "type": "text",
                    "is_secret": False,
                    "label_key": "ai_model",
                    "placeholder": f"e.g. {DEFAULT_OLLAMA_MODEL}",
                    "required": False,
                },
            ],
        }

    @property
    def capabilities(self) -> dict[str, Any]:
        return {
            "supports_tools": self.supports_tools,
            "max_context_tokens": None,
        }

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        from core.models import AppSettings

        chat_url = f"{self.base_url}/api/chat"
        model_name = str(kwargs.get("model") or self.model or "").strip()
        # For chat generation, allow up to 180s (3 minutes) by default to accommodate local LLMs
        timeout = int(kwargs.get("timeout") or max(self.timeout, 180))

        options: dict[str, Any] = {}
        try:
            options["num_predict"] = int(kwargs.get("max_tokens") or AppSettings.get("ai_max_tokens", "2048"))
        except (ValueError, TypeError):
            pass
        try:
            options["temperature"] = float(kwargs.get("temperature") or AppSettings.get("ai_temperature", "0.7"))
        except (ValueError, TypeError):
            pass
        try:
            options["num_ctx"] = int(kwargs.get("context_size") or AppSettings.get("ai_context_size", "4096"))
        except (ValueError, TypeError):
            pass

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "stream": False,
        }
        if options:
            payload["options"] = options
        if tools:
            payload["tools"] = tools

        data, status, err = make_json_http_request(
            url=chat_url,
            method="POST",
            payload=payload,
            timeout=timeout,
        )

        if err:
            safe_err = redact_secrets(err)
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": safe_err}

        if not isinstance(data, dict):
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": "Invalid JSON response from Ollama API."}

        msg = data.get("message", {})
        content = ""
        tool_calls = None
        if isinstance(msg, dict):
            content = str(msg.get("content", "")).strip()
            tool_calls = msg.get("tool_calls")
            if not tool_calls and content and content.startswith("{") and ("function" in content or "name" in content):
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        fn_name = parsed.get("function") or parsed.get("name")
                        fn_args = parsed.get("parameters") or parsed.get("arguments") or {}
                        if isinstance(fn_name, str) and fn_name and isinstance(fn_args, dict):
                            tool_calls = [{"function": {"name": fn_name, "arguments": fn_args}}]
                            content = ""
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

        prompt_eval = data.get("prompt_eval_count")
        eval_count = data.get("eval_count")

        return {
            "content": content,
            "tool_calls": tool_calls,
            "prompt_tokens": int(prompt_eval) if isinstance(prompt_eval, (int, float)) else None,
            "completion_tokens": int(eval_count) if isinstance(eval_count, (int, float)) else None,
            "error": None,
        }


