"""Ollama NDJSON chat streaming, used only by the optional voice path."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Callable

from core.integrations.ai_provider.ollama_options import build_options
from core.integrations.ai_provider.ollama_payload import (
    apply_runtime_flags,
    format_timing,
    is_think_unsupported_error,
    native_messages,
    think_setting,
)
from core.services.ai.credential_encryption import redact_secrets

logger = logging.getLogger(__name__)


def _consume(response, result: dict[str, Any], on_text, model: str) -> bool:
    try:
        with response:
            for line in response:
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    result["error"] = "Ollama returned an invalid streaming response."
                    return False
                if not isinstance(chunk, dict):
                    result["error"] = "Ollama returned an invalid streaming response."
                    return False
                if chunk.get("error"):
                    result["error"] = redact_secrets(str(chunk["error"]))
                    return False
                message = chunk.get("message") or {}
                if isinstance(message, dict):
                    text = str(message.get("content") or "")
                    result["content"] += text
                    if text and on_text:
                        try:
                            on_text(text)
                        except Exception:
                            logger.exception("Optional voice sentence callback failed")
                    result["tool_calls"].extend(message.get("tool_calls") or [])
                for field, key in (("prompt_eval_count", "prompt_tokens"), ("eval_count", "completion_tokens")):
                    value = chunk.get(field)
                    if isinstance(value, (int, float)):
                        result[key] = int(value)
                if chunk.get("done"):
                    result["tool_calls"] = result["tool_calls"] or None
                    logger.warning(format_timing(model, chunk))
                    return True
    except (urllib.error.URLError, TimeoutError, OSError):
        result["error"] = "Ollama streaming request failed or timed out."
    return False


def generate_stream(provider, messages: list[dict[str, Any]], tools=None, on_text: Callable[[str], None] | None = None,
                    **kwargs: Any) -> dict[str, Any]:
    from core.models import AppSettings

    model = str(kwargs.get("model") or provider.model or "").strip()
    payload: dict[str, Any] = {
        "model": model,
        "messages": native_messages(messages),
        "stream": True,
    }
    options = build_options(kwargs, provider.user_options)
    if options:
        payload["options"] = options
    if tools:
        payload["tools"] = tools
    keep_alive = provider.user_options.get("keep_alive") or AppSettings.get("ai_keep_alive", None)
    apply_runtime_flags(payload, model, keep_alive, think_setting(), kwargs.get("reasoning"))
    timeout = int(kwargs.get("timeout") or max(provider.timeout, 180))
    result: dict[str, Any] = {
        "content": "", "tool_calls": [], "prompt_tokens": None,
        "completion_tokens": None, "error": None,
    }
    url = f"{provider.base_url}/api/chat"

    for attempt in range(2):
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": provider.user_agent},
            method="POST",
        )
        try:
            response = urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as exc:
            detail = exc.read(2048).decode("utf-8", errors="replace")
            if attempt == 0 and "think" in payload and is_think_unsupported_error(detail):
                payload.pop("think", None)
                continue
            result["error"] = f"Ollama streaming request failed (HTTP {exc.code})."
            return result
        except (urllib.error.URLError, TimeoutError, OSError):
            result["error"] = "Ollama streaming request failed or timed out."
            return result

        if _consume(response, result, on_text, model):
            return result
        if not result["error"]:
            result["error"] = "Ollama ended the stream before completing the response."
        return result

    result["error"] = "Ollama streaming request failed."
    return result
