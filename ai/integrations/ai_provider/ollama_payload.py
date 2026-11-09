"""Runtime flags for Ollama /api/chat payloads (thinking toggle, keep_alive)."""

from __future__ import annotations

import json
import re
from typing import Any

THINK_MODES = ("auto", "on", "off")   # Settings > AI Advisor > "Reasoning (thinking)": auto = on where the caller asks for it

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


def resolve_think(setting: Any, reasoning: str | None = None) -> bool:
    """Whether a call thinks. on/off always win; auto follows the caller's own hint (reasoning="on" for the agent loop and for
    document writing; no hint or "off" for one-word classifier questions, translation and plain chat)."""
    mode = str(setting or "auto").strip().lower()
    return True if mode == "on" else False if mode == "off" else reasoning == "on"


def think_setting() -> str:
    from core.models import AppSettings

    mode = str(AppSettings.get("ai_think", "auto", user=None) or "auto").strip().lower()
    return mode if mode in THINK_MODES else "auto"


def native_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The history with every tool call's arguments as an object (Ollama rejects a JSON string there); other messages unchanged."""
    out = []
    for m in messages:
        calls = m.get("tool_calls") if isinstance(m, dict) else None
        if not calls:
            out.append(m)
            continue
        fixed = []
        for c in calls:
            fn = dict(c.get("function") or {}) if isinstance(c, dict) else {}
            args = fn.get("arguments")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {}
            fixed.append({**c, "function": {**fn, "arguments": args if isinstance(args, dict) else {}}})
        out.append({**m, "tool_calls": fixed})
    return out


def apply_runtime_flags(payload: dict[str, Any], model: str, keep_alive: Any, think: Any = "auto",
                        reasoning: str | None = None) -> dict[str, Any]:
    """Add think (qwen3 only, see resolve_think) and keep_alive to a chat payload, in place."""
    if supports_think_toggle(model):
        payload["think"] = resolve_think(think, reasoning)
    ka = normalize_keep_alive(keep_alive)
    if ka is not None:
        payload["keep_alive"] = ka
    return payload


def is_think_unsupported_error(err: Any) -> bool:
    return "think" in str(err or "").lower()


def format_timing(model: str, data: dict[str, Any]) -> str:
    """One-line per-call timing from Ollama's own counters (durations are nanoseconds)."""
    def sec(key: str) -> float:
        v = data.get(key)
        return float(v) / 1e9 if isinstance(v, (int, float)) else 0.0

    return (
        f"[AI-TIMING] model={model} prompt_tokens={data.get('prompt_eval_count')} "
        f"prompt_eval={sec('prompt_eval_duration'):.1f}s gen_tokens={data.get('eval_count')} "
        f"gen={sec('eval_duration'):.1f}s load={sec('load_duration'):.1f}s total={sec('total_duration'):.1f}s"
    )
