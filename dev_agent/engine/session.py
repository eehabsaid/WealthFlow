"""One model conversation (a phase): ask, parse, run the tool, feed the clipped result back, until the model answers `final`/`plan` or is stopped.
Guards against loops: invalid replies, the same call repeated, and a step limit."""

from __future__ import annotations

import json
from dataclasses import dataclass

from ..providers.base import ProviderError
from .attachments import AttachmentError
from .cancel import Cancelled
from ..tools import call
from .budget import Budget, ContextOverflow, clip_text
from .protocol import NUDGE, parse_reply


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


def run_phase(ctx, provider, system: str, first_user: str, accept: set[str], max_steps: int, attach: bool = True) -> PhaseResult:
    s = ctx.settings
    first = {"role": "user", "content": first_user}
    if attach and getattr(ctx, "attachments", None):
        try:
            first = ctx.attachments.message(first_user, provider.has_vision())
        except AttachmentError as exc:
            return PhaseResult("stopped", reason=str(exc))
    budget, messages = Budget(s["context_window"], s["reserve_tokens"]), [first]
    invalid, repeats, last_key = 0, 0, None
    for _ in range(max_steps):
        if ctx.cancel.is_set():
            return PhaseResult("stopped", reason=ctx.cancel.reason)
        try:
            budget.compact(system, messages)
            reply = provider.complete(system, messages, cancel=ctx.cancel)
        except Cancelled:
            return PhaseResult("stopped", reason=ctx.cancel.reason or "stopped by user")
        except ContextOverflow as exc:
            return PhaseResult("stopped", reason=str(exc))
        except ProviderError as exc:
            return PhaseResult("stopped", reason=f"provider error: {exc}")
        if ctx.ledger:
            ctx.ledger.add_usage(reply.usage)
        messages.append({"role": "assistant", "content": reply.text})
        action = parse_reply(reply.text)
        if action.kind == "invalid":
            invalid += 1
            if ctx.ledger:
                ctx.ledger.event("invalid_reply", text=reply.text[:1500], note=str(action.payload)[:200])
            if invalid >= 3:
                return PhaseResult("stopped", reason=f"the model gave 3 replies in a row that were not valid protocol JSON ({action.payload})")
            messages.append({"role": "user", "content": f"{NUDGE} ({action.payload[:80]})"})
            continue
        invalid = 0
        if action.kind in accept:
            return PhaseResult(action.kind, action.payload)
        if action.kind != "tool":
            messages.append({"role": "user", "content": f"A '{action.kind}' reply is not accepted in this phase. Use a tool or reply with {sorted(accept)}."})
            continue
        name, args = action.payload
        key = name + json.dumps(args, sort_keys=True, default=str)
        repeats = repeats + 1 if key == last_key else 1
        last_key = key
        if repeats >= 4:
            return PhaseResult("stopped", reason=f"the model repeated the same call to {name} 4 times in a row")
        if repeats == 3:
            messages.append({"role": "user", "content": f"TOOL RESULT {name}:\nYou already made this exact call twice. Change approach or finish."})
            continue
        result = call(ctx, name, args)
        ctx.emit({"type": "tool", "name": name, "ok": "error" not in result, "args": _brief(args), "summary": _summary(name, result)})
        messages.append({"role": "user", "content": f"TOOL RESULT {name}:\n" + clip_text(json.dumps(result, ensure_ascii=False, default=str), s["max_tool_result_chars"])})
    return PhaseResult("stopped", reason=f"step limit ({max_steps}) reached")
