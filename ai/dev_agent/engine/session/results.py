"""Phase result, call summaries and the context event."""

from __future__ import annotations

import json
from dataclasses import dataclass

from ai.dev_agent.engine import meter
from ai.dev_agent.engine.budget import tokens


MAX_INVALID_TEXT, MAX_INVALID_NATIVE = 3, 5   # replies in a row that cannot be used before the phase stops
MAX_CALLS_PER_REPLY = 8
LENGTH_STOPS = {"length", "max_tokens", "max_output_tokens", "max_tokens_reached", "max_tokens_exceeded"}


@dataclass
class PhaseResult:
    kind: str                 # "final" | "plan" | "stopped"
    payload: object = None
    reason: str = ""
    messages: list | None = None   # the conversation at the end, so the next phase (fixing failed checks) can continue it


def _brief(args) -> str:
    text = json.dumps(args, ensure_ascii=False, default=str)
    return text if len(text) <= 240 else text[:237] + "..."


def _summary(name: str, result: dict) -> str:
    """One short line for the live feed (never file contents). An empty `error` (edit_files has the key even when all went well) is not an error."""
    if result.get("error"):
        return str(result["error"])[:240]
    if name == "edit_files":
        return ", ".join(f"{f['path']}: {f['state']}" for f in result.get("files", []))[:240]
    if name in ("edit_file", "write_file"):
        return f"{result.get('path')}: {result.get('state')}"
    if name in ("run_command", "git", "run_tests", "shell"):
        return f"{result.get('status')} (exit {result.get('exit_code')}, {result.get('duration_s')}s)" + (f", changed {len(result['files_changed'])} file(s)" if result.get("files_changed") else "")
    if name == "read_file":
        return f"{result.get('path')} lines {result.get('start')}-{result.get('end')} of {result.get('total_lines')}"
    if name in ("grep", "search_index", "web_search"):
        return f"{len(result.get('matches') or result.get('results') or [])} results"
    if name in ("glob", "list_dir"):
        return f"{len(result.get('files') or result.get('entries') or [])} entries"
    if name == "web_fetch":
        return f"{result.get('url')} ({len(result.get('text') or '')} chars)"
    if name == "todo":
        return f"{result.get('open')} open of {len(result.get('items') or [])}"
    return "ok"


def _context_event(ctx, trace, budget, system, messages, reply, label: str) -> None:
    estimate = budget.used(system, messages) + tokens(reply.text)   # messages do not hold the reply yet
    usage = reply.usage or {}
    snap = meter.snapshot(usage.get("input_tokens", 0), usage.get("output_tokens", 0), estimate, budget.window, budget.reserve)
    ctx.emit({"type": "context", "phase": label or "phase", "step": trace.step, **snap})
    trace.model(trace.step, reply, estimate)


class _Empty:
    text, usage, finish_reason = "", {}, ""
