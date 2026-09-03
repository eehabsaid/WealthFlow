"""Abstract base class for all AI provider implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


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
    def from_settings(cls) -> Optional["BaseAIProvider"]:
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
