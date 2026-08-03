"""
AI Provider abstraction layer.

Supports pluggable AI providers behind BaseAIProvider interface.
Default concrete provider: OllamaProvider (local / self-hosted Ollama instance).

Standard urllib.request is used for all outbound calls — zero external dependencies.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Optional, Type

logger = logging.getLogger(__name__)


class BaseAIProvider(ABC):
    """
    Abstract base class for all AI provider implementations.
    Future providers (OpenAI, Claude, Gemini) will inherit from this base class.
    """

    PROVIDER_NAME: str = "unknown"

    @abstractmethod
    def check_connection(self) -> dict[str, Any]:
        """
        Check reachability and version of the provider endpoint.
        Returns:
            {
                "reachable": bool,
                "version": str | None,
                "error": str | None,
                "response_time_ms": int,
            }
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


class OllamaProvider(BaseAIProvider):
    """
    Ollama implementation of BaseAIProvider.
    Interacts with Ollama's HTTP API (/api/version, /api/tags).
    """

    PROVIDER_NAME = "ollama"

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

    def check_connection(self) -> dict[str, Any]:
        start_time = time.perf_counter()
        version_url = f"{self.base_url}/api/version"
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}

        try:
            req = urllib.request.Request(version_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                return {
                    "reachable": True,
                    "version": data.get("version", "unknown"),
                    "error": None,
                    "response_time_ms": elapsed_ms,
                }
        except urllib.error.HTTPError as exc:
            # Fallback to /api/tags if /api/version returned 404 on older Ollama versions
            if exc.code == 404:
                return self._check_tags_connection(start_time)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return {
                "reachable": False,
                "version": None,
                "error": f"HTTP {exc.code}: {exc.reason}",
                "response_time_ms": elapsed_ms,
            }
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.warning("Ollama connection check failed for %s: %s", self.base_url, exc)
            return {
                "reachable": False,
                "version": None,
                "error": str(exc),
                "response_time_ms": elapsed_ms,
            }

    def _check_tags_connection(self, start_time: float) -> dict[str, Any]:
        tags_url = f"{self.base_url}/api/tags"
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        try:
            req = urllib.request.Request(tags_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                json.loads(resp.read().decode("utf-8"))
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                return {
                    "reachable": True,
                    "version": "unknown",
                    "error": None,
                    "response_time_ms": elapsed_ms,
                }
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return {
                "reachable": False,
                "version": None,
                "error": str(exc),
                "response_time_ms": elapsed_ms,
            }

    def list_models(self) -> list[dict[str, Any]]:
        tags_url = f"{self.base_url}/api/tags"
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        try:
            req = urllib.request.Request(tags_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("models", [])
                if isinstance(models, list):
                    return models
                return []
        except Exception as exc:
            logger.warning("Ollama list_models failed for %s: %s", self.base_url, exc)
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


AVAILABLE_AI_PROVIDERS: dict[str, Type[BaseAIProvider]] = {
    "ollama": OllamaProvider,
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
    Read AI settings from AppSettings and instantiate the active provider.
    Returns None if AI is disabled or provider key is unconfigured/unknown.
    """
    from core.models import AppSettings

    enabled_str = AppSettings.get("ai_enabled", "false").strip().lower()
    if enabled_str not in ("true", "1", "yes"):
        return None

    provider_key = AppSettings.get("ai_provider", "ollama").strip()
    ollama_url = AppSettings.get("ai_ollama_url", "http://localhost:11434").strip()
    model = AppSettings.get("ai_model", "llama3.2:latest").strip()

    try:
        timeout = int(AppSettings.get("ai_timeout", "15"))
    except (ValueError, TypeError):
        timeout = 15

    return get_ai_provider(provider_key, base_url=ollama_url, model=model, timeout=timeout)
