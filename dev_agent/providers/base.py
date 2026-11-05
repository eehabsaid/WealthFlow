"""One provider interface. The agent speaks a plain-text JSON protocol, so providers only move messages; there is no per-model logic."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class ProviderError(RuntimeError):
    pass


@dataclass
class Reply:
    text: str
    usage: dict = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})


def redact(text: str, secrets) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def merge_roles(messages: list[dict]) -> list[dict]:
    """Providers require alternating roles: merge consecutive messages of the same role."""
    out: list[dict] = []
    for msg in messages:
        if out and out[-1]["role"] == msg["role"]:
            out[-1] = {"role": msg["role"], "content": out[-1]["content"] + "\n\n" + msg["content"]}
        else:
            out.append({"role": msg["role"], "content": msg["content"]})
    return out


class Provider(ABC):
    name = ""

    def __init__(self, model: str, base_url: str, api_key: str = "", timeout: int = 3600, max_output: int = 4096, context_window: int = 150000):
        self.model, self.base_url, self.api_key = model, base_url.rstrip("/"), api_key
        self.timeout, self.max_output, self.context_window = timeout, max_output, context_window

    @abstractmethod
    def complete(self, system: str, messages: list[dict]) -> Reply:
        """Send the system prompt and user/assistant messages; return the reply text and token usage."""
