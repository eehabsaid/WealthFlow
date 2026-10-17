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
from .loop_helpers import compact, digest, label, publish_legacy, result_text, target, trim_history
from .actions import extract_calls, is_call_leak, salvage_content, strip_think, unavailable_tools
from .defs import investigation_tool_schemas
from .refusal import is_announcement, is_refusal

NUDGES, CALL_TIMEOUT_S = 2, 240


@dataclass
class Investigation:
    content: str = ""
    steps: list = field(default_factory=list)          # audit records of every executed tool call
    llm_calls: int = 0
    nudges: int = 0
    reason: str = "answered"                           # answered | budget | max_steps | provider_error | digest | cancelled
    error: str | None = None
    elapsed_s: float = 0.0
    results: list = field(default_factory=list)        # [(tool, args, text)] kept for the digest fallback
    native_tools: bool = True                          # False: the model was driven through the text-JSON protocol


def _progress(agent, user, conversation_id, step, max_steps, name, args, text_label, started, shown, status) -> None:
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


def investigate(provider, user, user_text: str, *, history=None, max_steps: int = 10, budget_s: int = 240,
                ctx_chars: int = 24000, require_evidence: bool = False, conversation_id=None,
                extra_refusal_markers: tuple = (), agent: bool = False, instructions: str | None = None, hint: str = "",
                max_reads: int | None = None, cancel_check=None) -> Investigation:
    from core.services.ai.tools import validate_and_execute_tool

    started = time.monotonic()
    out = Investigation()
    schemas = investigation_tool_schemas(user)
    names = {s["function"]["name"] for s in schemas}
    native = bool(getattr(provider, "supports_tools", False))
    out.native_tools = native
    system = prompt.build_agent_prompt(user, schemas, native, instructions) if agent else prompt.build_system_prompt(user, schemas, native)
    asked = user_text + (f"\n\n[HINT, not verified by you; confirm or extend it with tools: {hint}]" if hint else "")
    messages = [{"role": "system", "content": system}] + trim_history(history) + [{"role": "user", "content": asked}]
    seen: set = set()
    reads, shown = 0, []
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
        if cancel_check and cancel_check():
            out.reason = "cancelled"
            break
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
                if cancel_check and cancel_check():
                    out.reason = "cancelled"
                    break
                fp = f"{name}:{json.dumps(args, sort_keys=True, default=str)}"
                if fp in seen:
                    messages.append({"role": "system", "content": f"TOOL RESULT ({name}): you already made this exact call; its result is above. "
                                     "Use it, or call a different tool / different arguments."})
                    continue
                seen.add(fp)
                reads += name == "app_read_file"
                if max_reads and reads > max_reads:
                    out.steps.append({"tool": name, "status": "rejected", "rejection_reason": "read limit", "arguments": args, "step": step})
                    messages.append({"role": "system", "content": f"TOOL RESULT ({name}): the limit of {max_reads} file reads for this question "
                                     "is reached. Answer from what you have read, or search with app_grep instead."})
                    continue
                text_label = label(name, args)
                _progress(agent, user, conversation_id, step, max_steps, name, args, text_label, started, shown, "running")
                audit, tool_res = validate_and_execute_tool(name, args, user)
                audit["step"] = step
                out.steps.append(audit)
                text = result_text(tool_res, result_cap)
                out.results.append((name, args, text))
                _progress(agent, user, conversation_id, step, max_steps, name, args, text_label, started, shown,
                          "ok" if audit.get("status") == "success" else "failed")
                messages.append({"role": "system", "content": f"TOOL RESULT ({name} {json.dumps(args, default=str, ensure_ascii=False)[:140]}):\n{text}"})
            if out.reason == "cancelled":
                break
            compact(messages, ctx_chars)
            continue
        text = strip_think(res.get("content"))
        if text and is_call_leak(text):
            kept = salvage_content(text) if "generate_file" in names and "generate_file" in text else ""
            if kept:   # a whole document written inside the call and cut off: never show the call; the app writes the document itself
                out.content, out.reason = kept, "truncated_call"
                break
            if out.nudges < NUDGES:
                nudge("Your last reply was a tool call written as text that could not be read (cut off or not valid JSON). Call the tool "
                      "again with valid JSON and short arguments, or write the answer in plain text.")
                continue
            text = ""
        investigated = bool(out.steps)
        needs_evidence = require_evidence and not investigated
        if text and is_announcement(text) and out.nudges < NUDGES:
            file_hint = (" To create a file call generate_file now; for a written document (guide, report, summary) put the full text "
                         "you want in the file in its `content` argument." if "generate_file" in names else "")
            nudge("You announced a next step instead of doing it. Do not describe what you will do: call the tool in THIS reply, "
                  "or, if you already have everything, write the complete answer now." + file_hint)
            continue
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
    if out.reason == "cancelled":
        out.content = digest(out.results)   # the stage adds the localized "stopped" note; no further model call
        return out
    if out.reason == "answered":
        out.reason = "budget" if remaining() <= 20 else "max_steps" if step >= max_steps else "digest"
    if out.error and not out.steps:
        return out
    messages.append({"role": "system", "content": "Write your final answer now from the tool results above; do not call tools. "
                     "If something could not be determined, say exactly what you checked and what is missing."})
    final = call(None)
    text = strip_think(final.get("content")) if not final.get("error") else ""
    if text and (extract_calls(final, names) or is_call_leak(text)):
        text = ""   # even the tool-free call wrote a tool request instead of an answer: use the digest, never raw JSON
    out.content = text if text and not is_refusal(text, bool(out.steps), extra_refusal_markers) else digest(out.results)
    if not out.content:
        out.error = out.error or str(final.get("error") or "empty model reply")
    out.elapsed_s = time.monotonic() - started
    return out
