"""
Gemini (Google Generative AI) Provider Implementation.

Interacts with Google's Generative Language REST API via stdlib urllib.request.
Supports system instructions, message conversion, function declarations, token usage, and secret redaction.
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

GEMINI_DEFAULT_MODELS = [
    {"name": "gemini-1.5-pro", "model": "gemini-1.5-pro"},
    {"name": "gemini-1.5-flash", "model": "gemini-1.5-flash"},
    {"name": "gemini-2.0-flash", "model": "gemini-2.0-flash"},
]


class GeminiProvider(BaseAIProvider):
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

    @classmethod
    def from_settings(cls) -> Optional[GeminiProvider]:
        from core.models import AppSettings

        raw_key = AppSettings.get("ai_gemini_api_key", "").strip()
        api_key = decrypt_credential(raw_key)
        model = AppSettings.get("ai_gemini_model", "").strip()
        base_url = AppSettings.get("ai_gemini_base_url", "https://generativelanguage.googleapis.com/v1beta").strip()
        try:
            timeout = int(AppSettings.get("ai_timeout", "60"))
        except (ValueError, TypeError):
            timeout = 60

        return cls(api_key=api_key, model=model, base_url=base_url, timeout=timeout)

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        return {
            "key": cls.PROVIDER_NAME,
            "label_key": "ai_provider_gemini",
            "capabilities": {
                "supports_tools": True,
                "max_context_tokens": 1000000,
            },
            "fields": [
                {
                    "name": "ai_gemini_api_key",
                    "type": "password",
                    "is_secret": True,
                    "label_key": "ai_gemini_api_key",
                    "required": False,
                },
                {
                    "name": "ai_gemini_model",
                    "type": "text",
                    "is_secret": False,
                    "label_key": "ai_model",
                    "placeholder": "e.g. gemini-1.5-flash, gemini-1.5-pro",
                    "required": False,
                },
            ],
        }

    @property
    def capabilities(self) -> dict[str, Any]:
        return {
            "supports_tools": self.supports_tools,
            "max_context_tokens": 1000000,
        }

    def _convert_tools(self, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        decls = []
        for t in tools:
            if not isinstance(t, dict):
                continue
            fn = t.get("function", t)
            if isinstance(fn, dict):
                name = str(fn.get("name", "")).strip()
                desc = str(fn.get("description", "")).strip()
                params = fn.get("parameters") or {"type": "object", "properties": {}}
                if name:
                    decls.append({
                        "name": name,
                        "description": desc,
                        "parameters": params,
                    })
        if decls:
            return [{"functionDeclarations": decls}]
        return None

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not self.api_key:
            err = "Gemini API key is unconfigured or missing."
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": err}

        model_name = str(kwargs.get("model") or self.model or "").strip()
        if not model_name:
            err = "Gemini model name is unconfigured."
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": err}

        encoded_key = urllib.parse.quote(self.api_key)
        url = f"{self.base_url}/models/{model_name}:generateContent?key={encoded_key}"

        system_instruction = None
        contents: list[dict[str, Any]] = []

        for m in messages:
            if not isinstance(m, dict):
                continue
            role = str(m.get("role", "user")).lower()
            content = str(m.get("content", "")).strip()
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            else:
                g_role = "model" if role == "assistant" else "user"
                contents.append({"role": g_role, "parts": [{"text": content}]})

        if not contents:
            contents.append({"role": "user", "parts": [{"text": "Hello"}]})

        payload: dict[str, Any] = {"contents": contents}
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        g_tools = self._convert_tools(tools)
        if g_tools:
            payload["tools"] = g_tools

        secrets = [self.api_key]
        timeout = int(kwargs.get("timeout") or max(self.timeout, 120))
        data, status, err = make_json_http_request(
            url=url,
            method="POST",
            payload=payload,
            timeout=timeout,
            secrets=secrets,
        )

        if err:
            safe_err = redact_secrets(err, secrets)
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": safe_err}

        if not isinstance(data, dict):
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": "Invalid response format from Gemini API."}

        candidates = data.get("candidates", [])
        cand = candidates[0] if isinstance(candidates, list) and candidates else {}
        parts = cand.get("content", {}).get("parts", []) if isinstance(cand, dict) else []

        text_parts = []
        tool_calls = []

        if isinstance(parts, list):
            for p in parts:
                if not isinstance(p, dict):
                    continue
                if "text" in p:
                    text_parts.append(str(p["text"]).strip())
                elif "functionCall" in p:
                    fc = p["functionCall"]
                    if isinstance(fc, dict):
                        tool_calls.append({
                            "function": {
                                "name": fc.get("name"),
                                "arguments": fc.get("args", {}),
                            }
                        })

        content_res = "\n".join(text_parts).strip()
        usage = data.get("usageMetadata") or {}
        prompt_tokens = usage.get("promptTokenCount") if isinstance(usage, dict) else None
        completion_tokens = usage.get("candidatesTokenCount") if isinstance(usage, dict) else None

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
            return {"reachable": False, "version": None, "error": "Gemini API key is missing.", "response_time_ms": 0}

        secrets = [self.api_key]
        encoded_key = urllib.parse.quote(self.api_key)
        url = f"{self.base_url}/models?key={encoded_key}"

        data, status, err = make_json_http_request(url=url, method="GET", timeout=self.timeout, secrets=secrets)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if err:
            safe_err = redact_secrets(err, secrets)
            return {"reachable": False, "version": None, "error": safe_err, "response_time_ms": elapsed_ms}

        return {"reachable": True, "version": "v1beta", "error": None, "response_time_ms": elapsed_ms}

    def list_models(self) -> list[dict[str, Any]]:
        if not self.api_key:
            return list(GEMINI_DEFAULT_MODELS)

        secrets = [self.api_key]
        encoded_key = urllib.parse.quote(self.api_key)
        url = f"{self.base_url}/models?key={encoded_key}"

        data, status, err = make_json_http_request(url=url, method="GET", timeout=self.timeout, secrets=secrets)
        if err or not isinstance(data, dict):
            return list(GEMINI_DEFAULT_MODELS)

        models = data.get("models", [])
        if isinstance(models, list) and models:
            res = []
            for m in models:
                if isinstance(m, dict):
                    name_raw = str(m.get("name", "")).strip()
                    clean_name = name_raw.replace("models/", "") if name_raw.startswith("models/") else name_raw
                    if clean_name and "generateContent" in m.get("supportedGenerationMethods", []):
                        res.append({"name": clean_name, "model": clean_name})
            return res or list(GEMINI_DEFAULT_MODELS)
        return list(GEMINI_DEFAULT_MODELS)

    def check_model_available(self, model: str) -> bool:
        target = (model or self.model or "").strip().lower()
        if not target:
            return False
        return bool(self.api_key)
