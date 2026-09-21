"""Runtime flags for Ollama /api/chat payloads (thinking toggle, keep_alive)."""

from __future__ import annotations

import re
from typing import Any

# Ollama accepts Go durations ("30m", "1h30m") or a number of seconds (-1 = forever).
_DURATION_RE = re.compile(r"^(\d+(\.\d+)?(ns|us|µs|ms|s|m|h))+$")
_SECONDS_RE = re.compile(r"^-?\d+$")


def supports_think_toggle(model: str) -> bool:
    """True for model families whose hidden reasoning Ollama can switch off (qwen3)."""
    name = (model or "").strip().lower().split("/")[-1]
    return name.startswith("qwen3") and not name.startswith("qwen3-coder")


def normalize_keep_alive(value: Any) -> str | int | None:
    """Return a value Ollama accepts for keep_alive, or None to omit it."""
    text = str(value if value is not None else "").strip().lower()
    if not text:
        return None
    if _SECONDS_RE.match(text):
        return int(text)
    return text if _DURATION_RE.match(text) else None


def apply_runtime_flags(payload: dict[str, Any], model: str, keep_alive: Any) -> dict[str, Any]:
    """Add think=false (qwen3 only) and keep_alive to a chat payload, in place."""
    if supports_think_toggle(model):
        payload["think"] = False
    ka = normalize_keep_alive(keep_alive)
    if ka is not None:
        payload["keep_alive"] = ka
    return payload


def is_think_unsupported_error(err: Any) -> bool:
    return "think" in str(err or "").lower()
