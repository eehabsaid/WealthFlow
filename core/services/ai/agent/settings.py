"""Agent mode settings.

Global (sysadmin, Settings > AI Advisor): ai_agent_enabled, ai_agent_instructions ("" = built-in default), the step /
time / file-read limits. Per user: ai_chat_mode ("ask" = today's fast path, "agent" = the model investigates with tools),
remembered by the chat switch. Everyone may use Agent mode; the source-code tools stay sysadmin-only (see investigation.code_tools).
"""

from __future__ import annotations

from typing import Any

from core.integrations.ai_provider.ollama_payload import THINK_MODES, think_setting
from core.models import AppSettings

from .instructions import MAX_LENGTH

MODES = ("ask", "agent")
LIMITS = {"ai_agent_max_steps": (2, 40, 15), "ai_agent_budget_s": (60, 3600, 600), "ai_agent_max_reads": (1, 60, 12),
          "ai_document_budget_s": (120, 7200, 1200), "ai_document_max_tokens": (1024, 32768, 6000)}   # min, max, default
PROMPT_RESERVE = 3500   # tokens of the context window a document-writing prompt (screen data + app guide + rules) may take
_FALSE = ("false", "0", "no", "off")


def _global(key: str, default: str) -> str:
    return str(AppSettings.get(key, default, user=None) or default)


def agent_enabled() -> bool:
    return _global("ai_agent_enabled", "true").strip().lower() not in _FALSE


def stored_instructions() -> str:
    return str(AppSettings.get("ai_agent_instructions", "", user=None) or "").strip()


def stored_document_instructions() -> str:
    return str(AppSettings.get("ai_document_instructions", "", user=None) or "").strip()


def document_budget_s() -> int:
    return limits()["ai_document_budget_s"]


def document_max_tokens(provider=None) -> int:
    """Output tokens for one document-writing call: the setting, but never more than the context window leaves after the prompt
    (output beyond that is silently cut by the model server)."""
    want = limits()["ai_document_max_tokens"]
    ctx = (getattr(provider, "user_options", None) or {}).get("context_size") or AppSettings.get("ai_context_size", "4096", user=None)
    try:
        window = int(float(str(ctx)))
    except (ValueError, TypeError):
        window = 4096
    return max(1024, min(want, window - PROMPT_RESERVE))


def clamp(key: str, raw: Any) -> int:
    low, high, default = LIMITS[key]
    try:
        return max(low, min(high, int(float(str(raw)))))
    except ValueError:
        return default


def limits() -> dict[str, int]:
    return {key: clamp(key, _global(key, str(default))) for key, (_, _, default) in LIMITS.items()}


def get_agent_settings() -> dict[str, Any]:
    from .instructions import DEFAULT_DOCUMENT_INSTRUCTIONS, DEFAULT_INSTRUCTIONS

    return {"ai_agent_enabled": agent_enabled(), "ai_agent_instructions": stored_instructions(),
            "ai_agent_instructions_default": DEFAULT_INSTRUCTIONS, "ai_document_instructions": stored_document_instructions(),
            "ai_document_instructions_default": DEFAULT_DOCUMENT_INSTRUCTIONS, "ai_think": think_setting(), **limits()}


def validate_agent_settings(data: dict, current: dict) -> tuple[dict | None, str | None]:
    """(validated, error). Missing keys keep their current value."""
    enabled = data.get("ai_agent_enabled", current["ai_agent_enabled"])
    if isinstance(enabled, str):
        enabled = enabled.strip().lower() not in _FALSE
    text = str(data.get("ai_agent_instructions", current["ai_agent_instructions"]) or "").strip()
    if len(text) > MAX_LENGTH:
        return None, f"ai_agent_instructions must be at most {MAX_LENGTH} characters"
    doc_text = str(data.get("ai_document_instructions", current["ai_document_instructions"]) or "").strip()
    if len(doc_text) > MAX_LENGTH:
        return None, f"ai_document_instructions must be at most {MAX_LENGTH} characters"
    think = str(data.get("ai_think", current["ai_think"]) or "auto").strip().lower()
    if think not in THINK_MODES:
        return None, f"ai_think must be one of {list(THINK_MODES)}"
    out: dict[str, Any] = {"enabled": bool(enabled), "instructions": text, "document_instructions": doc_text, "think": think, "limits": {}}
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
    AppSettings.set("ai_document_instructions", validated["document_instructions"], user=None)
    AppSettings.set("ai_think", validated["think"], user=None)
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
