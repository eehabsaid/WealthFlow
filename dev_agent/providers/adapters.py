"""Transport adapters for Ollama, Anthropic, OpenAI and Gemini. Each only maps messages to that API's request and the reply back to text."""

from __future__ import annotations

from .base import Provider, ProviderError, Reply, merge_roles
from .http import post_json


class _Base(Provider):
    def _post(self, url: str, headers: dict, body: dict) -> dict:
        return post_json(url, headers, body, self.timeout, secrets=(self.api_key,), backoff=getattr(self, "backoff", 1.0))


class Ollama(_Base):
    name = "ollama"

    def complete(self, system, messages):
        body = {"model": self.model, "stream": False, "messages": [{"role": "system", "content": system}, *merge_roles(messages)],
                "options": {"num_ctx": self.context_window, "num_predict": self.max_output}}
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        data = self._post(f"{self.base_url}/api/chat", headers, body)
        try:
            return Reply(data["message"]["content"], {"input_tokens": data.get("prompt_eval_count", 0), "output_tokens": data.get("eval_count", 0)})
        except (KeyError, TypeError) as exc:
            raise ProviderError("unexpected Ollama reply shape") from exc


class Anthropic(_Base):
    name = "anthropic"

    def complete(self, system, messages):
        body = {"model": self.model, "max_tokens": self.max_output, "system": system, "messages": merge_roles(messages)}
        data = self._post(f"{self.base_url}/v1/messages", {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}, body)
        try:
            text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
            usage = data.get("usage", {})
            return Reply(text, {"input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0)})
        except (KeyError, TypeError, AttributeError) as exc:
            raise ProviderError("unexpected Anthropic reply shape") from exc


class OpenAI(_Base):
    name = "openai"

    def complete(self, system, messages):
        body = {"model": self.model, "max_completion_tokens": self.max_output,
                "messages": [{"role": "system", "content": system}, *merge_roles(messages)]}
        data = self._post(f"{self.base_url}/chat/completions", {"Authorization": f"Bearer {self.api_key}"}, body)
        try:
            usage = data.get("usage", {})
            return Reply(data["choices"][0]["message"]["content"] or "", {"input_tokens": usage.get("prompt_tokens", 0), "output_tokens": usage.get("completion_tokens", 0)})
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("unexpected OpenAI reply shape") from exc


class Gemini(_Base):
    name = "gemini"

    def complete(self, system, messages):
        contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in merge_roles(messages)]
        body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents, "generationConfig": {"maxOutputTokens": self.max_output}}
        data = self._post(f"{self.base_url}/v1beta/models/{self.model}:generateContent", {"x-goog-api-key": self.api_key}, body)
        try:
            text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
            usage = data.get("usageMetadata", {})
            return Reply(text, {"input_tokens": usage.get("promptTokenCount", 0), "output_tokens": usage.get("candidatesTokenCount", 0)})
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderError("unexpected Gemini reply shape") from exc
