"""
AI Provider abstraction layer.

Supports pluggable AI providers behind BaseAIProvider interface:
- OllamaProvider (local / self-hosted Ollama instance)
- OpenAIProvider (OpenAI Chat Completions API)
- ClaudeProvider (Anthropic Messages API)
- GeminiProvider (Google Generative AI REST API)
- AzureOpenAIProvider (Azure OpenAI Deployment API)

Standard urllib.request is used for all outbound calls — zero external dependencies.

Sibling modules:
- base.py: BaseAIProvider abstract interface
- ollama_provider.py: OllamaProvider implementation
- factory.py: AVAILABLE_AI_PROVIDERS registry, get_ai_provider(), get_active_ai_provider()
"""

from __future__ import annotations

from .base import BaseAIProvider
from .ollama_provider import OllamaProvider
from .factory import (
    AVAILABLE_AI_PROVIDERS,
    get_ai_provider,
    get_active_ai_provider,
    AzureOpenAIProvider,
    ClaudeProvider,
    GeminiProvider,
    OpenAIProvider,
)

__all__ = [
    "BaseAIProvider",
    "OllamaProvider",
    "AVAILABLE_AI_PROVIDERS",
    "get_ai_provider",
    "get_active_ai_provider",
    "AzureOpenAIProvider",
    "ClaudeProvider",
    "GeminiProvider",
    "OpenAIProvider",
]
