"""Context budgeting: a 150K window with 25-30K kept free for reasoning and final verification. Tokens are estimated as chars/4 (an estimate,
not a provider count). Old tool results are trimmed first, then the oldest exchanges are dropped; logs keep only errors and excerpts."""

from __future__ import annotations

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


class Budget:
    def __init__(self, window: int = 150000, reserve: int = 28000):
        self.window, self.reserve = window, reserve
        self.limit = window - reserve

    def used(self, system: str, messages: list[dict]) -> int:
        return tokens(system) + sum(tokens(m["content"]) + 4 + len(m.get("images", ())) * IMAGE_TOKENS for m in messages)

    def compact(self, system: str, messages: list[dict]) -> int:
        """Shrink `messages` in place until they fit; returns how many were touched. ContextOverflow if even the minimum does not fit."""
        touched = 0
        if self.used(system, messages) <= self.limit:
            return 0
        for i in range(1, max(1, len(messages) - 4)):
            msg = messages[i]
            if msg["content"].startswith("TOOL RESULT") and len(msg["content"]) > 700:
                messages[i] = {**msg, "content": clip_log(msg["content"], 600)}
                touched += 1
                if self.used(system, messages) <= self.limit:
                    return touched
        while len(messages) > 5 and self.used(system, messages) > self.limit:
            del messages[1:3]   # drop the oldest assistant/user exchange; roles keep alternating
            touched += 1
            messages[0] = {**messages[0], "content": messages[0]["content"] + "\n\n[earlier steps were dropped to save context; the task ledger above is the record]"} \
                if "earlier steps were dropped" not in messages[0]["content"] else messages[0]
        if self.used(system, messages) > self.limit:
            raise ContextOverflow(f"the work package does not fit the {self.limit}-token budget even after trimming; split the task into smaller steps")
        return touched
