"""One model conversation (a phase): ask, parse, run the tool, feed the clipped result back, until the model answers `final`/`plan` or is stopped.
Guards against loops: invalid replies, the same call repeated, and a step limit."""

from __future__ import annotations

import json
from dataclasses import dataclass

from ai.dev_agent.providers.base import ProviderError
from ai.dev_agent.engine.attachments import AttachmentError
from ai.dev_agent.engine.cancel import Cancelled
from ai.dev_agent.tools import call
from ai.dev_agent.engine import meter
from ai.dev_agent.engine.budget import Budget, ContextOverflow, clip_text, tokens
from ai.dev_agent.engine.trace import Trace
from ai.dev_agent.engine.protocol import error_details, nudge_for, parse_reply


@dataclass
class PhaseResult:
    kind: str                 # "final" | "plan" | "stopped"
    payload: object = None
    reason: str = ""


def _brief(args) -> str:
    text = json.dumps(args, ensure_ascii=False, default=str)
    return text if len(text) <= 240 else text[:237] + "..."


def _summary(name: str, result: dict) -> str:
    """One short line for the live feed (never file contents)."""
    if "error" in result:
        return str(result["error"])[:240]
    if name == "edit_files":
        return ", ".join(f"{f['path']}: {f['state']}" for f in result.get("files", []))[:240]
    if name in ("run_command", "git", "run_tests"):
        return f"{result.get('status')} (exit {result.get('exit_code')}, {result.get('duration_s')}s)"
    if name == "read_file":
        return f"{result.get('path')} lines {result.get('start')}-{result.get('end')} of {result.get('total_lines')}"
    if name in ("grep", "search_index"):
        return f"{len(result.get('matches') or result.get('results') or [])} results"
    return "ok"


def run_phase(ctx, provider, system: str, first_user: str, accept: set[str], max_steps: int, attach: bool = True, label: str = "") -> PhaseResult:
    """One conversation. Besides the live feed it writes the phase's full trace (engine/trace.py) and, after every model call, a `context` event
    with the real token usage (engine/meter.py)."""
    trace = Trace(ctx, provider, label)
    first = {"role": "user", "content": first_user}
    if attach and getattr(ctx, "attachments", None):
        try:
            first = ctx.attachments.message(first_user, provider.has_vision())
        except AttachmentError as exc:
            return PhaseResult("stopped", reason=str(exc))
    trace.start(system, first)
    result = _converse(ctx, provider, system, first, accept, max_steps, trace, label)
    trace.end(trace.step, result.kind, result.reason)
    return result


def _context_event(ctx, trace, budget, system, messages, reply, label: str) -> None:
    estimate = budget.used(system, messages) + tokens(reply.text)   # messages do not hold the reply yet
    usage = reply.usage or {}
    snap = meter.snapshot(usage.get("input_tokens", 0), usage.get("output_tokens", 0), estimate, budget.window, budget.reserve)
    ctx.emit({"type": "context", "phase": label or "phase", "step": trace.step, **snap})
    trace.model(trace.step, reply, estimate)


def _converse(ctx, provider, system: str, first: dict, accept: set[str], max_steps: int, trace: Trace, label: str) -> PhaseResult:
    s = ctx.settings
    budget, messages = Budget(s["context_window"], s["reserve_tokens"]), [first]
    invalid, repeats, last_key = 0, 0, None
    for step in range(1, max_steps + 1):
        trace.step = step
        if ctx.cancel.is_set():
            return PhaseResult("stopped", reason=ctx.cancel.reason)
        try:
            touched = budget.compact(system, messages)
            if touched:
                trace.compact(step, touched)
            reply = provider.complete(system, messages, cancel=ctx.cancel)
        except Cancelled:
            return PhaseResult("stopped", reason=ctx.cancel.reason or "stopped by user")
        except ContextOverflow as exc:
            return PhaseResult("stopped", reason=str(exc))
        except ProviderError as exc:
            return PhaseResult("stopped", reason=f"provider error: {exc}")
        if ctx.ledger:
            ctx.ledger.add_usage(reply.usage)
        _context_event(ctx, trace, budget, system, messages, reply, label)
        finish_reason = (getattr(reply, "finish_reason", "") or "").strip().lower()
        if finish_reason in {"length", "max_tokens", "max_output_tokens", "max_tokens_reached", "max_tokens_exceeded"}:
            if ctx.ledger:
                ctx.ledger.event("truncated_reply", finish_reason=finish_reason, chars=len(reply.text),
                                 output_tokens=(reply.usage or {}).get("output_tokens", 0),
                                 text=reply.text[:1500], tail=reply.text[-1500:])
            return PhaseResult("stopped", reason=f"provider stopped generation at its output limit ({finish_reason}); increase max_output_tokens or reduce the tool-call payload")
        messages.append({"role": "assistant", "content": reply.text})
        action = parse_reply(reply.text)
        if action.kind == "invalid":
            invalid += 1
            if ctx.ledger:
                details = error_details(action)
                ctx.ledger.event("invalid_reply", text=reply.text[:1500], tail=reply.text[-1500:],
                                 chars=len(reply.text), note=str(action.payload)[:200],
                                 finish_reason=getattr(reply, "finish_reason", "") or "",
                                 **details)
            if invalid >= 3:
                return PhaseResult("stopped", reason=f"the model gave 3 replies in a row that were not valid protocol JSON ({action.payload})")
            nudge = nudge_for(action)
            messages.append({"role": "user", "content": nudge})
            trace.message(step, "invalid_reply_nudge", nudge)
            continue
        invalid = 0
        if action.kind in accept:
            return PhaseResult(action.kind, action.payload)
        if action.kind != "tool":
            note = f"A '{action.kind}' reply is not accepted in this phase. Use a tool or reply with {sorted(accept)}."
            messages.append({"role": "user", "content": note})
            trace.message(step, "reply_not_accepted", note)
            continue
        name, args = action.payload
        key = name + json.dumps(args, sort_keys=True, default=str)
        repeats = repeats + 1 if key == last_key else 1
        last_key = key
        if repeats >= 4:
            return PhaseResult("stopped", reason=f"the model repeated the same call to {name} 4 times in a row")
        if repeats == 3:
            warn = f"TOOL RESULT {name}:\nYou already made this exact call twice. Change approach or finish."
            messages.append({"role": "user", "content": warn})
            trace.message(step, "repeat_warning", warn)
            continue
        result = call(ctx, name, args)
        ctx.emit({"type": "tool", "name": name, "ok": "error" not in result, "args": _brief(args), "summary": _summary(name, result)})
        content = f"TOOL RESULT {name}:\n" + clip_text(json.dumps(result, ensure_ascii=False, default=str), s["max_tool_result_chars"])
        messages.append({"role": "user", "content": content})
        trace.tool(step, name, args, result, content)
    return PhaseResult("stopped", reason=f"step limit ({max_steps}) reached")
