"""Response-message parsing for OllamaProvider.generate()."""

from __future__ import annotations

import json
from typing import Any


def parse_message(msg: Any) -> tuple[str, list | None]:
    """Return (content, tool_calls). Recovers a tool call the model wrote as
    plain JSON text instead of using the tool_calls field."""
    content = ""
    tool_calls = None
    if isinstance(msg, dict):
        content = str(msg.get("content", "")).strip()
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
