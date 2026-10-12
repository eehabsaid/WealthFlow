"""Tool-call extraction for local models: native `tool_calls`, or JSON written into the text (several shapes)."""

from __future__ import annotations

import json

from core.integrations.ai_provider.ollama_response import strip_reasoning

_NAME_KEYS = ("name", "tool", "tool_name", "function")
_ARG_KEYS = ("arguments", "parameters", "args", "input")
MAX_CALLS_PER_STEP = 3


def strip_think(text: str) -> str:
    """Reasoning-model scratchpad removed from visible text: one implementation, shared with the Ollama provider
    (<think> blocks, closing-tag-only builds, an unclosed block)."""
    return strip_reasoning(str(text or "")) or ""


def _balanced(text: str, start: int) -> str:
    depth = 0
    in_str = esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            esc = (ch == "\\" and not esc)
            if ch == '"' and not esc:
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start: i + 1]
    return ""


def _norm_native(call) -> tuple[str, dict]:
    if not isinstance(call, dict):
        return "", {}
    fn = call.get("function") if isinstance(call.get("function"), dict) else {}
    name = str(fn.get("name") or call.get("name") or "").strip()
    args = fn.get("arguments") if "arguments" in fn else call.get("arguments", {})
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            args = {}
    return name, args if isinstance(args, dict) else {}


def _from_text(content: str, valid: set) -> list[tuple[str, dict]]:
    found, pos = [], 0
    while True:
        start = (content or "").find("{", pos)
        if start < 0 or len(found) >= MAX_CALLS_PER_STEP:
            return found
        blob = _balanced(content, start)
        pos = start + (len(blob) or 1)
        try:
            obj = json.loads(blob)
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        name = next((str(obj[k]) for k in _NAME_KEYS if isinstance(obj.get(k), str) and obj[k] in valid), "")
        if not name:
            continue
        args = next((obj[k] for k in _ARG_KEYS if isinstance(obj.get(k), (dict, str))), {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError:
                args = {}
        found.append((name, args if isinstance(args, dict) else {}))


def extract_calls(result: dict, valid_names: set) -> list[tuple[str, dict]]:
    """[(tool_name, args)] the model asked for, at most MAX_CALLS_PER_STEP, restricted to the tools actually offered."""
    calls = [(n, a) for n, a in (_norm_native(c) for c in (result.get("tool_calls") or [])) if n in valid_names]
    if not calls:
        calls = _from_text(str(result.get("content") or ""), valid_names)
    return calls[:MAX_CALLS_PER_STEP]


def unavailable_tools(result: dict, valid_names: set) -> list[str]:
    """Tool names the model requested natively that were not offered (never executed; the loop tells the model)."""
    wanted = (_norm_native(c)[0] for c in (result.get("tool_calls") or []))
    return sorted({n for n in wanted if n and n not in valid_names})
