"""
Claude (Anthropic) Provider Implementation.

Interacts with Anthropic's Messages API (/v1/messages) via stdlib urllib.request.
Converts system prompts, messages, tool schemas, token usage tracking, and secret redaction.
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

CLAUDE_DEFAULT_MODELS = [
    {"name": "claude-3-5-sonnet-20241022", "model": "claude-3-5-sonnet-20241022"},
    {"name": "claude-3-5-haiku-20241022", "model": "claude-3-5-haiku-20241022"},
    {"name": "claude-3-opus-20240229", "model": "claude-3-opus-20240229"},
]


class ClaudeProvider(BaseAIProvider):
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

    @classmethod
    def from_settings(cls) -> Optional[ClaudeProvider]:
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

    def _convert_tools(self, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        converted = []
        for t in tools:
            if not isinstance(t, dict):
                continue
            fn = t.get("function", t)
            if isinstance(fn, dict):
                name = str(fn.get("name", "")).strip()
                desc = str(fn.get("description", "")).strip()
                params = fn.get("parameters") or {"type": "object", "properties": {}}
                if name:
                    converted.append({
                        "name": name,
                        "description": desc,
                        "input_schema": params,
                    })
        return converted or None

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not self.api_key:
            err = "Claude API key is unconfigured or missing."
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": err}

        model_name = str(kwargs.get("model") or self.model or "").strip()
        if not model_name:
            err = "Claude model name is unconfigured."
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": err}

        url = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        system_prompt = ""
        claude_msgs: list[dict[str, Any]] = []

        for m in messages:
            if not isinstance(m, dict):
                continue
            role = str(m.get("role", "user")).lower()
            content = str(m.get("content", "")).strip()
            if role == "system":
                system_prompt = f"{system_prompt}\n{content}".strip() if system_prompt else content
            else:
                c_role = "assistant" if role == "assistant" else "user"
                claude_msgs.append({"role": c_role, "content": content})

        if not claude_msgs:
            claude_msgs.append({"role": "user", "content": "Hello"})

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": claude_msgs,
            "max_tokens": int(kwargs.get("max_tokens") or 2048),
        }
        if system_prompt:
            payload["system"] = system_prompt

        c_tools = self._convert_tools(tools)
        if c_tools:
            payload["tools"] = c_tools

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
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": "Invalid response format from Anthropic API."}

        content_blocks = data.get("content", [])
        text_parts = []
        tool_calls = []

        if isinstance(content_blocks, list):
            for block in content_blocks:
                if not isinstance(block, dict):
                    continue
                b_type = block.get("type")
                if b_type == "text":
                    text_parts.append(str(block.get("text", "")).strip())
                elif b_type == "tool_use":
                    tool_calls.append({
                        "id": block.get("id"),
                        "function": {
                            "name": block.get("name"),
                            "arguments": block.get("input", {}),
                        }
                    })

        content_res = "\n".join(text_parts).strip()
        usage = data.get("usage") or {}
        prompt_tokens = usage.get("input_tokens") if isinstance(usage, dict) else None
        completion_tokens = usage.get("output_tokens") if isinstance(usage, dict) else None

        return {
            "content": content_res,
            "tool_calls": tool_calls if tool_calls else None,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "error": None,
        }

    def check_connection(self) -> dict[str, Any]:
        start = time.perf_counter()
        if not self.api_key:
            return {"reachable": False, "version": None, "error": "Claude API key is missing.", "response_time_ms": 0}

        secrets = [self.api_key]
        # Minimal messages ping request to test key validity
        url = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": self.model or "claude-3-5-haiku-20241022",
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
        }

        data, status, err = make_json_http_request(url=url, method="POST", headers=headers, payload=payload, timeout=self.timeout, secrets=secrets)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if err:
            safe_err = redact_secrets(err, secrets)
            return {"reachable": False, "version": None, "error": safe_err, "response_time_ms": elapsed_ms}

        return {"reachable": True, "version": "2023-06-01", "error": None, "response_time_ms": elapsed_ms}

    def list_models(self) -> list[dict[str, Any]]:
        # Anthropic does not have a public list models REST endpoint; return curated list
        return list(CLAUDE_DEFAULT_MODELS)

    def check_model_available(self, model: str) -> bool:
        target = (model or self.model or "").strip().lower()
        if not target:
            return False
        # If API key is present, accept valid model string format
        return bool(self.api_key)
