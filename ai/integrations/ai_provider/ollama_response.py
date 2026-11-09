"""Response-message parsing for OllamaProvider.generate()."""

from __future__ import annotations

import json
import re
from typing import Any

_THINK_BLOCK_RE = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.DOTALL | re.IGNORECASE)
_THINK_CLOSE_RE = re.compile(r"</think(?:ing)?>", re.IGNORECASE)
_THINK_OPEN_TAIL_RE = re.compile(r"<think(?:ing)?>.*\Z", re.DOTALL | re.IGNORECASE)


def strip_reasoning(text: str) -> str:
    """Remove a reasoning model's visible thinking from an answer.

    Handles <think>...</think> blocks, thinking-only builds that emit just the closing tag (everything
    before it is reasoning), and a thinking block that was cut off before it closed (all reasoning)."""
    if not text:
        return text
    out = _THINK_BLOCK_RE.sub("", text)
    closes = list(_THINK_CLOSE_RE.finditer(out))
    if closes:
        out = out[closes[-1].end():]
    out = _THINK_OPEN_TAIL_RE.sub("", out)
    return out.strip()


def parse_message(msg: Any) -> tuple[str, list | None]:
    """Return (content, tool_calls). Recovers a tool call the model wrote as
    plain JSON text instead of using the tool_calls field."""
    content = ""
    tool_calls = None
    if isinstance(msg, dict):
        content = strip_reasoning(str(msg.get("content", "")).strip())
        tool_calls = msg.get("tool_calls")
        if not tool_calls and content and content.startswith("{") and ("function" in content or "name" in content):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    fn_name = parsed.get("function") or parsed.get("name")
                    fn_args = parsed.get("parameters") or parsed.get("arguments") or {}
                    if isinstance(fn_name, str) and fn_name and isinstance(fn_args, dict):
                        tool_calls = [{"function": {"name": fn_name, "arguments": fn_args}}]
                        content = ""
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
    return content, tool_calls
