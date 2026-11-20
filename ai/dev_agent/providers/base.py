"""One provider interface. The agent speaks a plain-text JSON protocol, so providers only move messages; there is no per-model logic."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ai.dev_agent.providers import vision


class ProviderError(RuntimeError):
    pass


class MalformedOutput(ProviderError):
    """The model produced something the provider could not decode (e.g. Ollama: "error parsing tool call"). The loop feeds the message back to the model instead of stopping."""


class NoToolSupport(ProviderError):
    """The model/server does not accept the native tools API; the loop switches to the text protocol."""


@dataclass
class Reply:
    text: str
    usage: dict = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})
    finish_reason: str = ""
    raw: dict = field(default_factory=dict)   # the provider's own message object (e.g. Ollama's `message`), for the training trace
    tool_calls: list = field(default_factory=list)   # native tool calls: [{"id", "name", "args": dict}]; empty for the text protocol


def redact(text: str, secrets) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def merge_roles(messages: list[dict]) -> list[dict]:
    """Providers require alternating roles: merge consecutive messages of the same role. A message may carry `images` ([{mime, data(base64)}]).
    Native tool messages (an assistant message with `tool_calls`, and `tool` results) are never merged: they are passed through unchanged."""
    out: list[dict] = []
    for msg in messages:
        if msg["role"] == "tool" or msg.get("tool_calls"):
            out.append(dict(msg))
            continue
        images = list(msg.get("images", []))
        if out and out[-1]["role"] == msg["role"] and not out[-1].get("tool_calls"):
            images = out[-1].get("images", []) + images
            out[-1] = {"role": msg["role"], "content": out[-1]["content"] + "\n\n" + msg["content"]}
        else:
            out.append({"role": msg["role"], "content": msg["content"]})
        if images:
            out[-1]["images"] = images
    return out


class Provider(ABC):
    name = ""
    vision = None   # True/False forces the answer (tests); None = ask providers.vision
    native_tools = False   # True: `complete(..., tools=[...])` uses the provider's own tool-calling API and returns Reply.tool_calls

    def __init__(self, model: str, base_url: str, api_key: str = "", timeout: int = 3600, max_output: int = 4096, context_window: int = 150000):
        self.model, self.base_url, self.api_key = model, base_url.rstrip("/"), api_key
        self.timeout, self.max_output, self.context_window = timeout, max_output, context_window

    def request_meta(self) -> dict:
        """How this provider is called, for the training trace (never includes credentials)."""
        return {"provider": self.name, "model": self.model, "context_window": self.context_window, "max_output": self.max_output}

    def has_vision(self) -> bool:
        return self.vision if self.vision is not None else vision.supports_images(self.name, self.model, self.base_url)

    @abstractmethod
    def complete(self, system: str, messages: list[dict], cancel=None, tools: list[dict] | None = None) -> Reply:
        """Send the system prompt and the messages; return the reply text, native tool calls (when `tools` is given and the provider supports them) and token
        usage. `tools` = [{"name", "description", "parameters": JSON schema}]. `cancel` (a CancelToken) aborts the request."""
