"""The investigation loop: the local model explores the app with the read-only tools until it can answer.

Bounded three ways (steps, wall-clock budget, context size) and never ends on a refusal: a "can't / don't have" answer
is rejected with a nudge that points at the tools, up to NUDGES times. If the budget runs out, one last tool-free call
writes the answer from the evidence; if that also fails, the gathered results are returned as an honest digest.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from . import prompt
from .actions import extract_calls, strip_think, unavailable_tools
from .defs import investigation_tool_schemas
from .refusal import is_refusal

NUDGES, CALL_TIMEOUT_S = 2, 240
LABELS = {
    "app_list_dir": "Browsing {path}", "app_find_files": "Finding files ({pattern})", "app_grep": "Searching the code ({pattern})",
    "app_find_definition": "Locating {symbol}", "app_read_file": "Reading {path}", "app_knowledge_search": "Checking the app guide",
    "app_data_models": "Looking at your data tables", "app_data_query": "Querying {model}", "generate_file": "Building your {format} file",
}


@dataclass
class Investigation:
    content: str = ""
    steps: list = field(default_factory=list)          # audit records of every executed tool call
    llm_calls: int = 0
    nudges: int = 0
    reason: str = "answered"                           # answered | budget | max_steps | provider_error | digest
    error: str | None = None
    elapsed_s: float = 0.0
    results: list = field(default_factory=list)        # [(tool, args, text)] kept for the digest fallback


def _trim(history, limit: int = 4, chars: int = 1200) -> list:
    keep = [m for m in (history or []) if m.get("role") in ("user", "assistant") and str(m.get("content") or "").strip()]
    return [{"role": m["role"], "content": str(m["content"])[:chars]} for m in keep[-limit:]]


def _compact(messages: list, ctx_chars: int) -> None:
    """Shrink the oldest tool-result messages until the conversation fits the context budget."""
    def size() -> int:
        return sum(len(m["content"]) for m in messages)
    for m in messages:
        if size() <= ctx_chars:
            return
        if m["role"] == "system" and m["content"].startswith("TOOL RESULT") and len(m["content"]) > 500:
            head = m["content"].split("\n", 1)[0]
            m["content"] = f"{head}\n[older result trimmed to save context]"


def _result_text(tool_res: dict, limit: int) -> str:
    text = json.dumps(tool_res.get("data") if tool_res.get("ok") else {"error": tool_res.get("error")},
                      default=str, ensure_ascii=False, separators=(",", ":"))
    return text if len(text) <= limit else text[:limit] + f"…[cut {len(text) - limit} chars; narrow the call]"


def _label(name: str, args: dict) -> str:
    try:
        return LABELS.get(name, name).format(**{k: str(v)[:40] for k, v in {**{"path": "", "pattern": "", "symbol": "", "model": "", "format": ""}, **args}.items()})
    except (KeyError, IndexError, ValueError):
        return name


def _publish(user, conversation_id, step, max_steps, name, label, started) -> None:
    if conversation_id is None:
        return
    from core.services.ai.cache_manager import AICacheManager

    AICacheManager().set(f"ai_loop_progress:{user.id}:{conversation_id}", {
        "step": step, "max_steps": max_steps, "tool": name, "label": label, "status": "running",
        "elapsed_s": round(time.monotonic() - started, 1)}, ttl_seconds=1800.0)


def _digest(results: list) -> str:
    if not results:
        return ""
    parts = [f"- {name}({json.dumps(args, default=str, ensure_ascii=False)[:120]}): {text[:700]}" for name, args, text in results[-3:]]
    return "I investigated the app but could not finish the write-up in time. This is what I found:\n" + "\n".join(parts)


def investigate(provider, user, user_text: str, *, history=None, max_steps: int = 10, budget_s: int = 240,
                ctx_chars: int = 24000, require_evidence: bool = False, conversation_id=None,
                extra_refusal_markers: tuple = ()) -> Investigation:
    from core.services.ai.tools import validate_and_execute_tool

    started = time.monotonic()
    out = Investigation()
    schemas = investigation_tool_schemas(user)
    names = {s["function"]["name"] for s in schemas}
    native = bool(getattr(provider, "supports_tools", False))
    messages = [{"role": "system", "content": prompt.build_system_prompt(user, schemas, native)}] + _trim(history) \
        + [{"role": "user", "content": user_text}]
    seen: set = set()
    result_cap = max(2500, min(9000, ctx_chars // 4))

    def remaining() -> float:
        return budget_s - (time.monotonic() - started)

    def call(tools):
        out.llm_calls += 1
        res = provider.generate(messages, tools=tools, temperature=0.1, timeout=int(max(20, min(CALL_TIMEOUT_S, remaining()))))
        return res if isinstance(res, dict) else {}

    def nudge(text: str) -> None:
        out.nudges += 1
        messages.append({"role": "system", "content": text})

    step = 0
    while step < max_steps and remaining() > 20:
        res = call(schemas if native else None)
        if res.get("error"):
            out.error = str(res["error"])
            out.reason = "provider_error"
            break
        calls = extract_calls(res, names)
        missing = unavailable_tools(res, names)
        if missing and not calls:
            if out.nudges >= NUDGES:
                break   # keeps asking for tools it does not have: stop and write the answer from the evidence
            nudge(f"Tool(s) {', '.join(missing)} are not available to you. Available tools: {', '.join(sorted(names))}. "
                  "Use one of those to investigate, then answer.")
            continue
        if calls:
            step += 1
            messages.append({"role": "assistant", "content": "Calling " + "; ".join(
                f"{n}({json.dumps(a, default=str, ensure_ascii=False)[:160]})" for n, a in calls)})
            for name, args in calls:
                fp = f"{name}:{json.dumps(args, sort_keys=True, default=str)}"
                if fp in seen:
                    messages.append({"role": "system", "content": f"TOOL RESULT ({name}): you already made this exact call; its result is above. "
                                     "Use it, or call a different tool / different arguments."})
                    continue
                seen.add(fp)
                _publish(user, conversation_id, step, max_steps, name, _label(name, args), started)
                audit, tool_res = validate_and_execute_tool(name, args, user)
                audit["step"] = step
                out.steps.append(audit)
                text = _result_text(tool_res, result_cap)
                out.results.append((name, args, text))
                messages.append({"role": "system", "content": f"TOOL RESULT ({name} {json.dumps(args, default=str, ensure_ascii=False)[:140]}):\n{text}"})
            _compact(messages, ctx_chars)
            continue
        text = strip_think(res.get("content"))
        investigated = bool(out.steps)
        needs_evidence = require_evidence and not investigated
        if (not text or needs_evidence or is_refusal(text, investigated, extra_refusal_markers)) and out.nudges < NUDGES:
            first = "app_data_models" if "app_data_models" in names else sorted(names)[0]
            nudge("You DO have full read access through your tools. Do not say you lack tools, data or access, and do not answer from memory. "
                  f"Investigate now: call a tool (for example {first} or app_knowledge_search"
                  f"{', app_grep' if 'app_grep' in names else ''}), read the result, then answer from it.")
            continue
        if text and not is_refusal(text, investigated, extra_refusal_markers):
            out.content = text
            break
        break  # still empty/refusing after the nudges: fall through to the forced final answer
    out.elapsed_s = time.monotonic() - started
    if out.content:
        return out
    if out.reason == "answered":
        out.reason = "budget" if remaining() <= 20 else "max_steps" if step >= max_steps else "digest"
    if out.error and not out.steps:
        return out
    messages.append({"role": "system", "content": "Write your final answer now from the tool results above; do not call tools. "
                     "If something could not be determined, say exactly what you checked and what is missing."})
    final = call(None)
    text = strip_think(final.get("content")) if not final.get("error") else ""
    if text and extract_calls(final, names):
        text = ""   # even the tool-free call wrote a tool request instead of an answer: use the digest, never raw JSON
    out.content = text if text and not is_refusal(text, bool(out.steps), extra_refusal_markers) else _digest(out.results)
    if not out.content:
        out.error = out.error or str(final.get("error") or "empty model reply")
    out.elapsed_s = time.monotonic() - started
    return out
