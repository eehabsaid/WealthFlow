"""Provider registry and factory functions for AI provider instantiation."""

from __future__ import annotations

from typing import Any, Optional, Type

from core.integrations.azure_openai_provider import AzureOpenAIProvider
from core.integrations.claude_provider import ClaudeProvider
from core.integrations.gemini_provider import GeminiProvider
from core.integrations.openai_provider import OpenAIProvider

from .base import BaseAIProvider
from .ollama_provider import OllamaProvider

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
