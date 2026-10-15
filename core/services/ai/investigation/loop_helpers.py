"""Small helpers of the investigation loop: history trimming, context compaction, step labels, digest."""

from __future__ import annotations

import json
import time

LABELS = {
    "app_list_dir": "Browsing {path}", "app_find_files": "Finding files ({pattern})", "app_grep": "Searching the code ({pattern})",
    "app_find_definition": "Locating {symbol}", "app_read_file": "Reading {path}", "app_knowledge_search": "Checking the app guide",
    "app_data_models": "Looking at your data tables", "app_data_query": "Querying {model}", "generate_file": "Building your {format} file",
    "app_computed_figures": "Computing your figures", "app_routes": "Looking up the app screens", "app_i18n_search": "Searching the UI text",
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
    for m in messages:
        if size() <= ctx_chars:
            return
        if m["role"] == "system" and m["content"].startswith("TOOL RESULT") and len(m["content"]) > 500:
            head = m["content"].split("\n", 1)[0]
            m["content"] = f"{head}\n[older result trimmed to save context]"


def result_text(tool_res: dict, limit: int) -> str:
    text = json.dumps(tool_res.get("data") if tool_res.get("ok") else {"error": tool_res.get("error")},
                      default=str, ensure_ascii=False, separators=(",", ":"))
    return text if len(text) <= limit else text[:limit] + f"…[cut {len(text) - limit} chars; narrow the call]"


def label(name: str, args: dict) -> str:
    blank = {"path": "", "pattern": "", "symbol": "", "model": "", "format": "", "feature": ""}
    try:
        return LABELS.get(name, name).format(**{k: str(v)[:40] for k, v in {**blank, **args}.items()})
    except (KeyError, IndexError, ValueError):
        return name


def target(args: dict) -> str:
    """The one argument that tells the user what a step is about (shown in the live step list, translated in the browser)."""
    for key in ("path", "pattern", "symbol", "model", "feature", "query", "term", "question", "format"):
        if args.get(key):
            return str(args[key])[:40]
    return ""


def digest(results: list) -> str:
    if not results:
        return ""
    parts = [f"- {name}({json.dumps(args, default=str, ensure_ascii=False)[:120]}): {text[:700]}" for name, args, text in results[-3:]]
    return "I investigated the app but could not finish the write-up in time. This is what I found:\n" + "\n".join(parts)


def publish_legacy(user, conversation_id, step, max_steps, name, label_text, started) -> None:
    """Progress for the non-agent investigator (single current step)."""
    if conversation_id is None:
        return
    from core.services.ai.cache_manager import AICacheManager

    AICacheManager().set(f"ai_loop_progress:{user.id}:{conversation_id}", {
        "step": step, "max_steps": max_steps, "tool": name, "label": label_text, "status": "running",
        "elapsed_s": round(time.monotonic() - started, 1)}, ttl_seconds=1800.0)
