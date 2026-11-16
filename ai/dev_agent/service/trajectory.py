"""Rebuilds complete model conversations from a task's events.jsonl (the `trace` events written by engine/trace.py) for training export.

Pure functions, events in and plain dicts out; no model, no repo access. A phase is one conversation with one system prompt. Its `messages` are what the
loop appended, in order: the first user message, then (assistant reply, user "TOOL RESULT ..." message) pairs, ending with the assistant's `final`/`plan`.
[system] + messages is what the provider received at its last call, except that secrets and personal data are masked in the log (engine/trace.py).
A phase is `clean` only when nothing in it needs explaining to a model: no invalid reply, nudge or repeat warning, no trimmed history, no stop."""

from __future__ import annotations

import json
from pathlib import Path


def read_events(path) -> list[dict]:
    """Every event of a task in file order. A missing file gives [], a torn or foreign line is skipped, never raised."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    events = []
    for line in text.splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            events.append(rec)
    return events


def _new(event: dict, index: int) -> dict:
    return {"index": index, "label": str(event.get("phase") or "phase"), "system": str(event.get("system") or ""),
            "messages": [{"role": "user", "content": str(m.get("content") or "")} for m in event.get("messages") or [] if isinstance(m, dict)],
            "request": event.get("request") or {}, "images": int(event.get("images") or 0), "steps": 0, "tools": [], "results": [], "tool_errors": 0,
            "usage": {"input_tokens": 0, "output_tokens": 0}, "ended": "", "reason": "", "exact": True, "clean": True, "notes": [],
            "redactions": int(event.get("redactions") or 0), "truncated": bool(event.get("truncated"))}


def _note(phase: dict, text: str) -> None:
    phase["clean"] = False
    if text not in phase["notes"]:
        phase["notes"].append(text)


def _apply(phase: dict, event: dict) -> None:
    kind = event.get("kind")
    phase["redactions"] += int(event.get("redactions") or 0)
    phase["truncated"] = phase["truncated"] or bool(event.get("truncated"))
    if kind == "model":
        phase["steps"] += 1
        phase["messages"].append({"role": "assistant", "content": str(event.get("reply") or "")})
        for key in ("input_tokens", "output_tokens"):
            phase["usage"][key] += int((event.get("usage") or {}).get(key) or 0)
        if event.get("exact") is False:
            phase["exact"] = False
    elif kind == "tool_result":
        phase["tools"].append(str(event.get("tool") or ""))
        phase["results"].append({"tool": phase["tools"][-1], "args": event.get("args") or {}, "ok": bool(event.get("ok", True)), "result": event.get("result") or {}})
        phase["tool_errors"] += 0 if event.get("ok", True) else 1
        phase["messages"].append({"role": "user", "content": str(event.get("message") or "")})
    elif kind == "message":   # a nudge, an "unaccepted reply" note or a repeat warning: the model went wrong here
        phase["messages"].append({"role": "user", "content": str(event.get("message") or "")})
        _note(phase, str(event.get("why") or "extra message"))
    elif kind == "compact":
        phase["exact"] = False
        _note(phase, "history was trimmed")
    elif kind == "phase_end":
        phase["ended"], phase["reason"] = str(event.get("result") or ""), str(event.get("reason") or "")
        if phase["ended"] not in ("final", "plan"):
            _note(phase, f"stopped: {phase['reason'] or 'no reason recorded'}")


def phases(events: list[dict]) -> list[dict]:
    """The phases of a task in the order they ran. A phase that never reached phase_end (the run died) has ended == '' and is never clean."""
    out: list[dict] = []
    for event in events:
        if event.get("type") != "trace":
            continue
        if event.get("kind") == "phase_start":
            out.append(_new(event, len(out)))
        elif out:
            _apply(out[-1], event)
    for phase in out:
        if not phase["ended"]:
            _note(phase, "never finished")
        if not phase["exact"]:
            phase["clean"] = False
    return out


def conversation(phase: dict) -> list[dict]:
    """The training format: system prompt first, then the loop's messages, roles as the Ollama provider sends them."""
    return [{"role": "system", "content": phase["system"]}, *phase["messages"]]


def alternates(messages: list[dict]) -> bool:
    """True when the messages after the system prompt strictly alternate user / assistant, starting with the user."""
    body = [m["role"] for m in messages if m["role"] != "system"]
    return bool(body) and all(role == ("user", "assistant")[i % 2] for i, role in enumerate(body))
