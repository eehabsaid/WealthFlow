"""Transport adapters for Ollama, Anthropic, OpenAI and Gemini. Each only maps messages to that API's request and the reply back to text."""

from __future__ import annotations

from ai.dev_agent.providers.base import Provider, ProviderError, Reply, merge_roles
from ai.dev_agent.providers.http import post_json


def _anthropic(m):
    if not m.get("images"):
        return {"role": m["role"], "content": m["content"]}
    parts = [{"type": "image", "source": {"type": "base64", "media_type": i["mime"], "data": i["data"]}} for i in m.get("images", ())]
    return {"role": m["role"], "content": [*parts, {"type": "text", "text": m["content"]}]}


def _ollama(m):
    return {"role": m["role"], "content": m["content"], **({"images": [i["data"] for i in m.get("images", ())]} if m.get("images") else {})}


def _openai(m):
    if not m.get("images"):
        return {"role": m["role"], "content": m["content"]}
    parts = [{"type": "image_url", "image_url": {"url": f"data:{i['mime']};base64,{i['data']}"}} for i in m.get("images", ())]
    return {"role": m["role"], "content": [{"type": "text", "text": m["content"]}, *parts]}


def _gemini(m):
    parts = [{"text": m["content"]}, *({"inline_data": {"mime_type": i["mime"], "data": i["data"]}} for i in m.get("images", ()))]
    return {"role": "model" if m["role"] == "assistant" else "user", "parts": parts}


class _Base(Provider):
    cancel = None

    def _post(self, url: str, headers: dict, body: dict) -> dict:
        return post_json(url, headers, body, self.timeout, secrets=(self.api_key,), backoff=getattr(self, "backoff", 1.0), cancel=self.cancel)


class Ollama(_Base):
    name = "ollama"

    def complete(self, system, messages, cancel=None):
        self.cancel = cancel
        body = {"model": self.model, "stream": False, "messages": [{"role": "system", "content": system}, *(_ollama(m) for m in merge_roles(messages))],
                "format": "json", "options": {"num_ctx": self.context_window, "num_predict": self.max_output}}
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        data = self._post(f"{self.base_url}/api/chat", headers, body)
        try:
            return Reply(data["message"]["content"], {"input_tokens": data.get("prompt_eval_count", 0), "output_tokens": data.get("eval_count", 0)},
                         str(data.get("done_reason") or ""))
        except (KeyError, TypeError) as exc:
            raise ProviderError("unexpected Ollama reply shape") from exc


class Anthropic(_Base):
    name = "anthropic"

    def complete(self, system, messages, cancel=None):
        self.cancel = cancel
        body = {"model": self.model, "max_tokens": self.max_output, "system": system, "messages": [_anthropic(m) for m in merge_roles(messages)]}
        data = self._post(f"{self.base_url}/v1/messages", {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}, body)
        try:
            text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
            usage = data.get("usage", {})
            return Reply(text, {"input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0)},
                         str(data.get("stop_reason") or ""))
        except (KeyError, TypeError, AttributeError) as exc:
            raise ProviderError("unexpected Anthropic reply shape") from exc


class OpenAI(_Base):
    name = "openai"

    def complete(self, system, messages, cancel=None):
        self.cancel = cancel
        body = {"model": self.model, "max_completion_tokens": self.max_output,
                "messages": [{"role": "system", "content": system}, *(_openai(m) for m in merge_roles(messages))]}
        data = self._post(f"{self.base_url}/chat/completions", {"Authorization": f"Bearer {self.api_key}"}, body)
        try:
            usage = data.get("usage", {})
            choice = data["choices"][0]
            return Reply(choice["message"]["content"] or "", {"input_tokens": usage.get("prompt_tokens", 0), "output_tokens": usage.get("completion_tokens", 0)},
                         str(choice.get("finish_reason") or ""))
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("unexpected OpenAI reply shape") from exc


class Gemini(_Base):
    name = "gemini"

    def complete(self, system, messages, cancel=None):
        self.cancel = cancel
        contents = [_gemini(m) for m in merge_roles(messages)]
        body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents, "generationConfig": {"maxOutputTokens": self.max_output}}
        data = self._post(f"{self.base_url}/v1beta/models/{self.model}:generateContent", {"x-goog-api-key": self.api_key}, body)
        try:
            text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
            usage = data.get("usageMetadata", {})
            candidate = data["candidates"][0]
            return Reply(text, {"input_tokens": usage.get("promptTokenCount", 0), "output_tokens": usage.get("candidatesTokenCount", 0)},
                         str(candidate.get("finishReason") or ""))
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderError("unexpected Gemini reply shape") from exc
