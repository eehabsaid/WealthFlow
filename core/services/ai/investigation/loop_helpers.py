"""Small helpers of the investigation loop: history trimming, context compaction, step labels, digest."""

from __future__ import annotations

import json
import time

from . import native_protocol

LABELS = {
    "app_list_dir": "Browsing {path}", "app_find_files": "Finding files ({pattern})", "app_grep": "Searching the code ({pattern})",
    "app_find_definition": "Locating {symbol}", "app_read_file": "Reading {path}", "app_knowledge_search": "Checking the app guide",
    "app_data_models": "Looking at your data tables", "app_data_query": "Querying {model}", "generate_file": "Building your {format} file",
    "app_computed_figures": "Computing your figures", "app_screen_data": "Reading the screen data ({path}{search})", "app_routes": "Looking up the app screens", "app_i18n_search": "Searching the UI text",
    "app_callers": "Finding where {symbol} is used", "app_git_history": "Reading the history of {path}",
    "app_trace_feature": "Tracing the feature ({feature})",
}


def trim_history(history, limit: int = 4, chars: int = 1200) -> list:
    keep = [m for m in (history or []) if m.get("role") in ("user", "assistant") and str(m.get("content") or "").strip()]
    return [{"role": m["role"], "content": str(m["content"])[:chars]} for m in keep[-limit:]]


def compact(messages: list, ctx_chars: int) -> None:
    """Shrink the oldest tool-result messages until the conversation fits the context budget."""
    def size() -> int:
        return sum(len(m["content"]) for m in messages)
    for i, m in enumerate(messages):
        if size() <= ctx_chars:
            return
        if native_protocol.is_result(m) and len(m["content"]) > 500:
            messages[i] = native_protocol.trimmed(m)


def asked_text(user_text: str, hint: str = "") -> str:
    """The user turn exactly as the model receives it (the unverified HINT block is part of it)."""
    return user_text + (f"\n\n[HINT, not verified by you; confirm or extend it with tools: {hint}]" if hint else "")


def result_text(tool_res: dict, limit: int) -> str:
    text = json.dumps(tool_res.get("data") if tool_res.get("ok") else {"error": tool_res.get("error")},
                      default=str, ensure_ascii=False, separators=(",", ":"))
    return text if len(text) <= limit else text[:limit] + f"…[cut {len(text) - limit} chars; narrow the call]"


def label(name: str, args: dict) -> str:
    blank = {"path": "", "pattern": "", "symbol": "", "model": "", "format": "", "feature": "", "search": ""}
    try:
        return LABELS.get(name, name).format(**{k: str(v)[:40] for k, v in {**blank, **args}.items()})
    except (KeyError, IndexError, ValueError):
        return name


def target(args: dict) -> str:
    """The one argument that tells the user what a step is about (shown in the live step list, translated in the browser)."""
    for key in ("path", "pattern", "symbol", "model", "feature", "search", "query", "term", "question", "format"):
        if args.get(key):
            return str(args[key])[:40]
    return ""


def digest(results: list) -> str:
    if not results:
        return ""
    parts = [f"- {name}({json.dumps(args, default=str, ensure_ascii=False)[:120]}): {text[:700]}" for name, args, text in results[-3:]]
    return "I investigated the app but could not finish the write-up in time. This is what I found:\n" + "\n".join(parts)


def publish_legacy(user, conversation_id, step, max_steps, name, label_text, started) -> None:
    """Progress for the document phase and for the non-agent investigator (single current step). An Agent run's step list, Stop
    flag and start time are carried over, so a page opened or refreshed while the document is written still shows them."""
    if conversation_id is None:
        return
    from core.services.ai.cache_manager import AICacheManager

    cache, key = AICacheManager(), f"ai_loop_progress:{user.id}:{conversation_id}"
    previous = cache.get(key)
    state = {"step": step, "max_steps": max_steps, "tool": name, "label": label_text, "status": "running",
             "elapsed_s": round(time.monotonic() - started, 1)}
    if isinstance(previous, dict):
        state.update({k: previous[k] for k in ("steps", "can_stop", "started_at") if k in previous})
    cache.set(key, state, ttl_seconds=1800.0)


def progress(agent, user, conversation_id, step, max_steps, name, args, text_label, started, shown, status) -> None:
    """Agent: the chat shows every step (label + status) like Continue; the plain investigator keeps its single "current step"."""
    if not agent:
        if status == "running":
            publish_legacy(user, conversation_id, step, max_steps, name, text_label, started)
        return
    from core.services.ai.agent.control import publish

    if status == "running":
        shown.append({"n": len(shown) + 1, "tool": name, "label": text_label, "status": "running", "target": target(args)})
    elif shown:
        shown[-1]["status"] = status
    publish(user, conversation_id, step=step, max_steps=max_steps, tool=name, label=text_label, started=started, steps=shown)
