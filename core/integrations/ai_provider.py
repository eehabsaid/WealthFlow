"""
AI Provider abstraction layer.

Supports pluggable AI providers behind BaseAIProvider interface:
- OllamaProvider (local / self-hosted Ollama instance)
- OpenAIProvider (OpenAI Chat Completions API)
- ClaudeProvider (Anthropic Messages API)
- GeminiProvider (Google Generative AI REST API)
- AzureOpenAIProvider (Azure OpenAI Deployment API)

Standard urllib.request is used for all outbound calls — zero external dependencies.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Optional, Type

from core.integrations.provider_utils import make_json_http_request
from core.services.ai.credential_encryption import redact_secrets

logger = logging.getLogger(__name__)


class BaseAIProvider(ABC):
    """
    Abstract base class for all AI provider implementations.
    Every concrete provider MUST implement from_settings(), capabilities, get_config_schema(),
    check_connection(), list_models(), check_model_available(), and generate().
    """

    PROVIDER_NAME: str = "unknown"
    supports_tools: bool = False

    @classmethod
    @abstractmethod
    def from_settings(cls) -> Optional[BaseAIProvider]:
        """Construct provider instance from AppSettings configuration."""

    @property
    @abstractmethod
    def capabilities(self) -> dict[str, Any]:
        """Returns dict of capability flags (e.g. supports_tools, max_context_tokens)."""

    @classmethod
    @abstractmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """Returns provider configuration schema metadata for settings UI rendering."""

    @abstractmethod
    def check_connection(self) -> dict[str, Any]:
        """
        Check reachability and version of the provider endpoint.
        Returns:
            {"reachable": bool, "version": str | None, "error": str | None, "response_time_ms": int}
        Must never raise out to caller.
        """

    @abstractmethod
    def list_models(self) -> list[dict[str, Any]]:
        """
        Fetch available models for this provider.
        Returns a list of dicts describing available models.
        Must never raise out to caller.
        """

    @abstractmethod
    def check_model_available(self, model: str) -> bool:
        """
        Check if *model* is available on the provider.
        Must never raise out to caller.
        """

    @abstractmethod
    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate chat response for given message sequence.
        Returns:
            {"content": str, "tool_calls": list | None, "prompt_tokens": int | None, "completion_tokens": int | None, "error": str | None}
        Must never raise out to caller.
        """


class OllamaProvider(BaseAIProvider):
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
    def from_settings(cls) -> Optional[OllamaProvider]:
        from core.models import AppSettings

        base_url = AppSettings.get("ai_ollama_url", "http://localhost:11434").strip()
        model = AppSettings.get("ai_model", "llama3.2:latest").strip()
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
                    "placeholder": "e.g. llama3.2:latest",
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

    def check_connection(self) -> dict[str, Any]:
        start_time = time.perf_counter()
        version_url = f"{self.base_url}/api/version"

        data, status, err = make_json_http_request(url=version_url, method="GET", timeout=self.timeout)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        if not err and isinstance(data, dict):
            return {
                "reachable": True,
                "version": data.get("version", "unknown"),
                "error": None,
                "response_time_ms": elapsed_ms,
            }

        # Fallback to /api/tags if /api/version returned 404 or failed
        return self._check_tags_connection(start_time)

    def _check_tags_connection(self, start_time: float) -> dict[str, Any]:
        tags_url = f"{self.base_url}/api/tags"
        data, status, err = make_json_http_request(url=tags_url, method="GET", timeout=self.timeout)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        if not err and isinstance(data, dict):
            return {
                "reachable": True,
                "version": "unknown",
                "error": None,
                "response_time_ms": elapsed_ms,
            }

        safe_err = redact_secrets(err or "Connection failed")
        return {
            "reachable": False,
            "version": None,
            "error": safe_err,
            "response_time_ms": elapsed_ms,
        }

    def list_models(self) -> list[dict[str, Any]]:
        tags_url = f"{self.base_url}/api/tags"
        data, status, err = make_json_http_request(url=tags_url, method="GET", timeout=self.timeout)
        if not err and isinstance(data, dict):
            models = data.get("models", [])
            if isinstance(models, list):
                return models
        return []

    def check_model_available(self, model: str) -> bool:
        target_model = (model or self.model or "").strip().lower()
        if not target_model:
            return False

        models = self.list_models()
        for m in models:
            name = str(m.get("name", "")).strip().lower()
            model_id = str(m.get("model", "")).strip().lower()
            if target_model in (name, model_id):
                return True
            if ":" not in target_model and (name.startswith(f"{target_model}:") or model_id.startswith(f"{target_model}:")):
                return True
        return False


from core.integrations.azure_openai_provider import AzureOpenAIProvider
from core.integrations.claude_provider import ClaudeProvider
from core.integrations.gemini_provider import GeminiProvider
from core.integrations.openai_provider import OpenAIProvider

AVAILABLE_AI_PROVIDERS: dict[str, Type[BaseAIProvider]] = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
    "azure": AzureOpenAIProvider,
}


def get_ai_provider(provider_key: str, **kwargs: Any) -> Optional[BaseAIProvider]:
    """
    Construct a provider instance given a provider key and configuration kwargs.
    Returns None if provider_key is unknown.
    """
    cls = AVAILABLE_AI_PROVIDERS.get((provider_key or "").strip().lower())
    if not cls:
        return None
    return cls(**kwargs)


def get_active_ai_provider() -> Optional[BaseAIProvider]:
    """
    Read AI settings from AppSettings and instantiate the active provider via from_settings().
    Returns None if AI is disabled or provider key is unconfigured/unknown.
    Zero provider-specific branches exist in this factory.
    """
    from core.models import AppSettings

    enabled_str = AppSettings.get("ai_enabled", "false").strip().lower()
    if enabled_str not in ("true", "1", "yes"):
        return None

    provider_key = AppSettings.get("ai_provider", "ollama").strip().lower()
    cls = AVAILABLE_AI_PROVIDERS.get(provider_key)
    if not cls:
        return None
    return cls.from_settings()
