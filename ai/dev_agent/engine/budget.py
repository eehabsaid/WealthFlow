"""Context budgeting: a 150K window with 25-30K kept free for reasoning and final verification. Tokens are estimated as chars/4 (an estimate,
not a provider count). Old tool results are trimmed first, then the oldest exchanges are dropped; logs keep only errors and excerpts."""

from __future__ import annotations

import json
import re

from ai.dev_agent.engine.attachments import IMAGE_TOKENS

IMPORTANT = re.compile(r"error|fail|traceback|exception|assert|warning|✖|not found|denied", re.I)


class ContextOverflow(RuntimeError):
    pass


def tokens(text: str) -> int:
    return len(text) // 4 + 1


def clip_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    head, tail = int(max_chars * 0.6), int(max_chars * 0.4)
    return f"{text[:head]}\n...[{len(text) - head - tail} chars omitted]...\n{text[-tail:]}"


def clip_log(text: str, max_chars: int) -> str:
    """Keep the first lines, every error-like line with its neighbour, and the last lines; never the whole log."""
    if len(text) <= max_chars:
        return text
    lines = text.splitlines()
    keep = set(range(min(5, len(lines)))) | set(range(max(0, len(lines) - 15), len(lines)))
    for i, line in enumerate(lines):
        if IMPORTANT.search(line):
            keep |= {max(0, i - 1), i, min(len(lines) - 1, i + 1)}
    out, last = [], -1
    for i in sorted(keep):
        if i != last + 1:
            out.append(f"...[{i - last - 1} lines omitted]...")
        out.append(lines[i])
        last = i
    if last < len(lines) - 1:
        out.append(f"...[{len(lines) - 1 - last} lines omitted]...")
    return clip_text("\n".join(out), max_chars)


MARK = "[earlier steps were dropped to save context"
KEEP_TURNS = 2     # the newest turns are never dropped or clipped
RECENT = 6         # the newest messages keep their full tool results


def _size(msg: dict) -> int:
    calls = msg.get("tool_calls")
    extra = tokens(json.dumps(calls, ensure_ascii=False, default=str)) if calls else 0
    return tokens(msg["content"] or "") + 4 + extra + len(msg.get("images", ())) * IMAGE_TOKENS


def _is_result(msg: dict) -> bool:
    return msg["role"] == "tool" or (msg["role"] == "user" and msg["content"].startswith("TOOL RESULT"))


def _describe(msg: dict) -> str:
    """A few words about a dropped assistant message: which tool it called and on what."""
    calls = msg.get("tool_calls")
    if calls:
        return ", ".join(f"{c['name']}({_target(c['args'])})" for c in calls[:3])
    try:
        obj = json.loads(msg["content"])
        if isinstance(obj, dict) and isinstance(obj.get("tool"), str):
            return f"{obj['tool']}({_target(obj.get('args'))})"
    except ValueError:
        pass
    return "reply"


def _target(args) -> str:
    if not isinstance(args, dict):
        return ""
    for key in ("path", "command", "pattern", "query", "url", "task"):
        if args.get(key):
            return str(args[key])[:60]
    if isinstance(args.get("edits"), list):
        return ",".join(str(e.get("path")) for e in args["edits"][:3] if isinstance(e, dict))[:60]
    return ""


class Budget:
    """Keeps a conversation inside the window minus the reserve (150K window, ~28K reserve by default). Order of measures: (1) results of old tool calls are clipped to their
    errors and ends, (2) the oldest turns (an assistant message with its tool results) are dropped and listed in one note in the first message. The newest turns stay intact."""

    def __init__(self, window: int = 150000, reserve: int = 28000):
        self.window, self.reserve = window, reserve
        self.limit = window - reserve
        self.dropped: list[str] = []

    def used(self, system: str, messages: list[dict]) -> int:
        return tokens(system) + sum(_size(m) for m in messages)

    def _turn_end(self, messages: list[dict], start: int) -> int:
        end = start + 1
        while end < len(messages) and messages[end]["role"] != "assistant":
            end += 1
        return end

    def _note(self, messages: list[dict]) -> None:
        head = messages[0]["content"].split("\n\n" + MARK)[0]
        listed = "; ".join(self.dropped[-12:])
        more = f" ({len(self.dropped)} in all)" if len(self.dropped) > 12 else ""
        messages[0] = {**messages[0], "content": f"{head}\n\n{MARK}; the task ledger above and the files on disk are the record. Dropped{more}: {listed[:900]}]"}

    def compact(self, system: str, messages: list[dict]) -> int:
        """Shrink `messages` in place until they fit; returns how many were touched. ContextOverflow if even the minimum does not fit."""
        touched = 0
        if self.used(system, messages) <= self.limit:
            return 0
        for i in range(1, max(1, len(messages) - RECENT)):
            msg = messages[i]
            if _is_result(msg) and len(msg["content"]) > 700:
                messages[i] = {**msg, "content": clip_log(msg["content"], 600)}
                touched += 1
                if self.used(system, messages) <= self.limit:
                    return touched
        while self.used(system, messages) > self.limit and sum(m["role"] == "assistant" for m in messages[1:]) > KEEP_TURNS:
            start = next((i for i in range(1, len(messages)) if messages[i]["role"] == "assistant"), None)
            if start is None:
                break
            end = self._turn_end(messages, start)
            self.dropped.append(_describe(messages[start]))
            del messages[start:end]
            if messages[1:2] and messages[1]["role"] != "assistant":   # text-mode nudges left in front of the next turn: they belong to the dropped one
                nxt = next((i for i in range(1, len(messages)) if messages[i]["role"] == "assistant"), len(messages))
                del messages[1:nxt]
            touched += 1
            self._note(messages)   # the note is part of what has to fit
        if self.used(system, messages) > self.limit:
            raise ContextOverflow(f"the conversation does not fit the {self.limit}-token budget even after trimming; split the task into smaller steps")
        return touched
