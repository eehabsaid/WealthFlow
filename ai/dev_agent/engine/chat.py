"""A chat is a thread of tasks: every follow-up the owner sends is a new task that carries the same `chat_id`. This builds the short text that tells
the planner what the earlier tasks of the chat asked and did, so a follow-up continues the conversation instead of starting from nothing."""

from __future__ import annotations

from ai.dev_agent.ledger.ledger import Ledger

MAX_TASKS, MAX_CHARS = 6, 6000


def chat_of(data: dict) -> str:
    return data.get("chat_id") or data["id"]   # tasks created before chats existed are chats of one


def _key(data: dict) -> tuple:
    return (data.get("order", 0), data["id"])   # `order` has nanosecond resolution: task ids only have seconds


def members(project, chat_id: str, before: dict | None = None) -> list[dict]:
    """Ledger data of the chat's tasks, oldest first. `before` = the data of a task: only the tasks created before it."""
    out = []
    for task_id in Ledger.list_ids(project):
        try:
            data = Ledger.load(project, task_id).data
        except FileNotFoundError:
            continue
        if chat_of(data) == chat_id and (before is None or _key(data) < _key(before)):
            out.append(data)
    return sorted(out, key=_key)


def _entry(n: int, d: dict) -> str:
    lines = [f"[{n}] OWNER ASKED: {d['goal'][:400]}", f"    STATUS: {d['status']}" + (f" - {d['stop_reason'][:200]}" if d.get("stop_reason") else "")]
    if d.get("answer"):
        lines.append(f"    ANSWER GIVEN: {str(d['answer'])[:600]}")
    elif d.get("plan"):
        lines.append(f"    PLAN: {d['plan']['summary'][:400]}")
    done = [f"{p['id']} {p['title']}: {p['summary']}" if p.get("summary") else f"{p['id']} {p['title']}" for p in d.get("packages", []) if p.get("status") == "done"]
    if done:
        lines.append("    DONE: " + "; ".join(done)[:600])
    files = sorted(d.get("files", {}))
    if files:
        lines.append("    FILES TOUCHED: " + ", ".join(files[:15]) + (f" (+{len(files) - 15} more)" if len(files) > 15 else ""))
    return "\n".join(lines)


def context(project, chat_id: str, before: dict | None = None) -> str:
    """'' for a first message. Newest entries win when the text would be too long."""
    every = members(project, chat_id, before)
    tasks = every[-MAX_TASKS:]
    first = len(every) - len(tasks) + 1
    entries = [_entry(first + i, d) for i, d in enumerate(tasks)]
    while len(entries) > 1 and sum(len(e) + 1 for e in entries) > MAX_CHARS:
        entries.pop(0)
    return "\n".join(entries)[-MAX_CHARS:]
