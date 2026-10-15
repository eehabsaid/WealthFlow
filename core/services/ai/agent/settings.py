"""Agent mode settings.

Global (sysadmin, Settings > AI Advisor): ai_agent_enabled, ai_agent_instructions ("" = built-in default), the step /
time / file-read limits. Per user: ai_chat_mode ("ask" = today's fast path, "agent" = the model investigates with tools),
remembered by the chat switch. Everyone may use Agent mode; the source-code tools stay sysadmin-only (see investigation.code_tools).
"""

from __future__ import annotations

from typing import Any

from core.models import AppSettings

from .instructions import MAX_LENGTH

MODES = ("ask", "agent")
LIMITS = {"ai_agent_max_steps": (2, 40, 15), "ai_agent_budget_s": (60, 3600, 600), "ai_agent_max_reads": (1, 60, 12)}   # min, max, default
_FALSE = ("false", "0", "no", "off")


def _global(key: str, default: str) -> str:
    return str(AppSettings.get(key, default, user=None) or default)


def agent_enabled() -> bool:
    return _global("ai_agent_enabled", "true").strip().lower() not in _FALSE


def stored_instructions() -> str:
    return str(AppSettings.get("ai_agent_instructions", "", user=None) or "").strip()


def clamp(key: str, raw: Any) -> int:
    low, high, default = LIMITS[key]
    try:
        return max(low, min(high, int(float(str(raw)))))
    except ValueError:
        return default


def limits() -> dict[str, int]:
    return {key: clamp(key, _global(key, str(default))) for key, (_, _, default) in LIMITS.items()}


def get_agent_settings() -> dict[str, Any]:
    from .instructions import DEFAULT_INSTRUCTIONS

    return {"ai_agent_enabled": agent_enabled(), "ai_agent_instructions": stored_instructions(),
            "ai_agent_instructions_default": DEFAULT_INSTRUCTIONS, **limits()}


def validate_agent_settings(data: dict, current: dict) -> tuple[dict | None, str | None]:
    """(validated, error). Missing keys keep their current value."""
    enabled = data.get("ai_agent_enabled", current["ai_agent_enabled"])
    if isinstance(enabled, str):
        enabled = enabled.strip().lower() not in _FALSE
    text = str(data.get("ai_agent_instructions", current["ai_agent_instructions"]) or "").strip()
    if len(text) > MAX_LENGTH:
        return None, f"ai_agent_instructions must be at most {MAX_LENGTH} characters"
    out: dict[str, Any] = {"enabled": bool(enabled), "instructions": text, "limits": {}}
    for key in LIMITS:
        raw = data.get(key, current[key])
        try:
            float(str(raw))
        except ValueError:
            return None, f"{key} must be a number"
        out["limits"][key] = clamp(key, raw)
    return out, None


def persist_agent_settings(validated: dict) -> None:
    AppSettings.set("ai_agent_enabled", "true" if validated["enabled"] else "false", user=None)
    AppSettings.set("ai_agent_instructions", validated["instructions"], user=None)
    for key, value in validated["limits"].items():
        AppSettings.set(key, str(value), user=None)


def get_chat_mode(user) -> str:
    mode = str(AppSettings.get("ai_chat_mode", "ask", user=user) or "ask").strip().lower()
    return mode if mode in MODES else "ask"


def set_chat_mode(user, mode: str) -> str:
    mode = mode if mode in MODES else "ask"
    AppSettings.set("ai_chat_mode", mode, user=user)
    return mode


def agent_active(user, requested: Any = None) -> bool:
    """Agent mode applies when the feature is on and the user's chat switch (or this request) says "agent"."""
    asked = str(requested or "").strip().lower()
    return agent_enabled() and (asked if asked in MODES else get_chat_mode(user)) == "agent"
