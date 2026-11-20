"""Transport adapters for Ollama, Anthropic, OpenAI and Gemini. Each maps messages (plain or native tool messages, see toolmsg.py) to that API's request and the
reply back to text + native tool calls. With `tools` the provider's own tool-calling API is used; without, the plain-text protocol."""

from __future__ import annotations

from ai.dev_agent.providers.base import MalformedOutput, NoToolSupport, Provider, ProviderError, Reply, merge_roles
from ai.dev_agent.providers.http import post_json
from ai.dev_agent.providers.toolmsg import decode_args, new_id, to_text


def _anthropic(m):
    if not m.get("images"):
        return {"role": m["role"], "content": m["content"]}
    parts = [{"type": "image", "source": {"type": "base64", "media_type": i["mime"], "data": i["data"]}} for i in m.get("images", ())]
    return {"role": m["role"], "content": [*parts, {"type": "text", "text": m["content"]}]}


def _anthropic_all(messages):
    """Native tool messages: tool_use blocks in the assistant message; the results of one turn go back together in ONE user message."""
    out: list[dict] = []
    for m in merge_roles(messages):
        if m["role"] == "tool":
            block = {"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"]}
            if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list) and out[-1].get("_results"):
                out[-1]["content"].append(block)
            else:
                out.append({"role": "user", "content": [block], "_results": True})
        elif m.get("tool_calls"):
            blocks = ([{"type": "text", "text": m["content"]}] if m["content"] else []) + [{"type": "tool_use", "id": c["id"], "name": c["name"], "input": c["args"]} for c in m["tool_calls"]]
            out.append({"role": "assistant", "content": blocks})
        else:
            msg = _anthropic(m)
            if out and out[-1].get("_results") and msg["role"] == "user":   # text after tool results shares their user message
                out[-1]["content"].extend(msg["content"] if isinstance(msg["content"], list) else [{"type": "text", "text": msg["content"]}])
            else:
                out.append(msg)
    return [{k: v for k, v in m.items() if k != "_results"} for m in out]


def _ollama(m):
    return {"role": m["role"], "content": m["content"], **({"images": [i["data"] for i in m.get("images", ())]} if m.get("images") else {})}


def _ollama_all(messages):
    out = []
    for m in merge_roles(messages):
        if m["role"] == "tool":
            out.append({"role": "tool", "tool_name": m.get("name", ""), "content": m["content"]})
        elif m.get("tool_calls"):
            out.append({"role": "assistant", "content": m["content"], "tool_calls": [{"function": {"name": c["name"], "arguments": c["args"]}} for c in m["tool_calls"]]})
        else:
            out.append(_ollama(m))
    return out


def _openai(m):
    if not m.get("images"):
        return {"role": m["role"], "content": m["content"]}
    parts = [{"type": "image_url", "image_url": {"url": f"data:{i['mime']};base64,{i['data']}"}} for i in m.get("images", ())]
    return {"role": m["role"], "content": [{"type": "text", "text": m["content"]}, *parts]}


def _openai_all(messages):
    import json
    out = []
    for m in merge_roles(messages):
        if m["role"] == "tool":
            out.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]})
        elif m.get("tool_calls"):
            out.append({"role": "assistant", "content": m["content"] or None,
                        "tool_calls": [{"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": json.dumps(c["args"], ensure_ascii=False)}} for c in m["tool_calls"]]})
        else:
            out.append(_openai(m))
    return out


def _gemini(m):
    parts = [{"text": m["content"]}, *({"inline_data": {"mime_type": i["mime"], "data": i["data"]}} for i in m.get("images", ()))]
    return {"role": "model" if m["role"] == "assistant" else "user", "parts": parts}


def _gemini_all(messages):
    out = []
    for m in merge_roles(messages):
        if m["role"] == "tool":
            part = {"functionResponse": {"name": m.get("name", ""), "response": {"result": m["content"]}}}
            if out and out[-1].get("_results"):
                out[-1]["parts"].append(part)
            else:
                out.append({"role": "user", "parts": [part], "_results": True})
        elif m.get("tool_calls"):
            out.append({"role": "model", "parts": ([{"text": m["content"]}] if m["content"] else []) + [{"functionCall": {"name": c["name"], "args": c["args"]}} for c in m["tool_calls"]]})
        else:
            out.append(_gemini(m))
    return [{k: v for k, v in m.items() if k != "_results"} for m in out]


def _gemini_schema(schema):
    """Gemini accepts only a subset of JSON schema."""
    if isinstance(schema, dict):
        return {k: _gemini_schema(v) for k, v in schema.items() if k not in ("additionalProperties", "default", "minimum", "maximum", "minItems", "maxItems")}
    if isinstance(schema, list):
        return [_gemini_schema(v) for v in schema]
    return schema


class _Base(Provider):
    cancel = None

    def _post(self, url: str, headers: dict, body: dict) -> dict:
        return post_json(url, headers, body, self.timeout, secrets=(self.api_key,), backoff=getattr(self, "backoff", 1.0), cancel=self.cancel)

    def _messages(self, messages, tools):
        return messages if tools else to_text(messages)   # no tools API in use: tool messages go as the plain-text protocol


class Ollama(_Base):
    name = "ollama"
    native_tools = True

    def request_meta(self) -> dict:
        return {**super().request_meta(), "api": "/api/chat", "stream": False, "tools": "native", "options": {"num_ctx": self.context_window, "num_predict": self.max_output}}

    def complete(self, system, messages, cancel=None, tools=None):
        self.cancel = cancel
        body = {"model": self.model, "stream": False, "messages": [{"role": "system", "content": system}, *_ollama_all(self._messages(messages, tools))],
                "options": {"num_ctx": self.context_window, "num_predict": self.max_output}}
        if tools:
            body["tools"] = [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}} for t in tools]
        else:
            body["format"] = "json"
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        try:
            data = self._post(f"{self.base_url}/api/chat", headers, body)
        except ProviderError as exc:
            text = str(exc).lower()
            if tools and "does not support tools" in text:
                raise NoToolSupport(str(exc)) from exc
            if "error parsing tool call" in text:
                raise MalformedOutput("your last tool call could not be parsed by the server (" + str(exc)[:300] + "); send it again as a valid call with JSON arguments") from exc
            raise
        try:
            message = data["message"]
            calls = []
            for c in message.get("tool_calls") or []:
                fn = c["function"]
                calls.append({"id": c.get("id") or new_id(), "name": fn["name"], "args": decode_args(fn["name"], fn.get("arguments"))})
            return Reply(message.get("content") or "", {"input_tokens": data.get("prompt_eval_count", 0), "output_tokens": data.get("eval_count", 0)},
                         str(data.get("done_reason") or ""),
                         {"message": {k: v for k, v in message.items() if k != "content"}, "model": data.get("model"), **{k: data[k] for k in ("total_duration", "prompt_eval_duration", "eval_duration") if k in data}},
                         calls)
        except (KeyError, TypeError, AttributeError) as exc:
            raise ProviderError("unexpected Ollama reply shape") from exc


class Anthropic(_Base):
    name = "anthropic"
    native_tools = True

    def complete(self, system, messages, cancel=None, tools=None):
        self.cancel = cancel
        body = {"model": self.model, "max_tokens": self.max_output, "system": system, "messages": _anthropic_all(self._messages(messages, tools))}
        if tools:
            body["tools"] = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in tools]
        data = self._post(f"{self.base_url}/v1/messages", {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}, body)
        try:
            text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
            calls = [{"id": b["id"], "name": b["name"], "args": decode_args(b["name"], b.get("input"))} for b in data["content"] if b.get("type") == "tool_use"]
            usage = data.get("usage", {})
            return Reply(text, {"input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0)}, str(data.get("stop_reason") or ""), {}, calls)
        except (KeyError, TypeError, AttributeError) as exc:
            raise ProviderError("unexpected Anthropic reply shape") from exc


class OpenAI(_Base):
    name = "openai"
    native_tools = True

    def complete(self, system, messages, cancel=None, tools=None):
        self.cancel = cancel
        body = {"model": self.model, "max_completion_tokens": self.max_output,
                "messages": [{"role": "system", "content": system}, *_openai_all(self._messages(messages, tools))]}
        if tools:
            body["tools"] = [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}} for t in tools]
        data = self._post(f"{self.base_url}/chat/completions", {"Authorization": f"Bearer {self.api_key}"}, body)
        try:
            usage = data.get("usage", {})
            choice = data["choices"][0]
            msg = choice["message"]
            calls = [{"id": c["id"], "name": c["function"]["name"], "args": decode_args(c["function"]["name"], c["function"].get("arguments"))} for c in msg.get("tool_calls") or []]
            return Reply(msg.get("content") or "", {"input_tokens": usage.get("prompt_tokens", 0), "output_tokens": usage.get("completion_tokens", 0)},
                         str(choice.get("finish_reason") or ""), {}, calls)
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("unexpected OpenAI reply shape") from exc


class Gemini(_Base):
    name = "gemini"
    native_tools = True

    def complete(self, system, messages, cancel=None, tools=None):
        self.cancel = cancel
        body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": _gemini_all(self._messages(messages, tools)), "generationConfig": {"maxOutputTokens": self.max_output}}
        if tools:
            body["tools"] = [{"functionDeclarations": [{"name": t["name"], "description": t["description"], "parameters": _gemini_schema(t["parameters"])} for t in tools]}]
        data = self._post(f"{self.base_url}/v1beta/models/{self.model}:generateContent", {"x-goog-api-key": self.api_key}, body)
        try:
            candidate = data["candidates"][0]
            parts = candidate["content"].get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            calls = [{"id": new_id(), "name": p["functionCall"]["name"], "args": decode_args(p["functionCall"]["name"], p["functionCall"].get("args"))} for p in parts if "functionCall" in p]
            usage = data.get("usageMetadata", {})
            return Reply(text, {"input_tokens": usage.get("promptTokenCount", 0), "output_tokens": usage.get("candidatesTokenCount", 0)}, str(candidate.get("finishReason") or ""), {}, calls)
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderError("unexpected Gemini reply shape") from exc
