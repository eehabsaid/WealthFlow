"""Turns exported traces into training text with the MODEL'S OWN chat template, and finds the "assistant starts here" marker from that
template (no hardcoded markers), so only the assistant turns (tool calls and answers) are trained, never the system prompt, the user
question or the tool results."""

from __future__ import annotations

import json
import os

PROBE = "@@@"


def _render(tok, messages, enable_thinking, tools=None, generation=False):
    return tok.apply_chat_template(messages, tools=tools, tokenize=False, add_generation_prompt=generation, enable_thinking=enable_thinking)


def _common_prefix(a: str, b: str) -> str:
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1
    return a[:n]


def find_markers(tok, enable_thinking: bool) -> tuple[str, str]:
    """(user_marker, assistant_marker) read from the chat template; raises ValueError if the template does not behave as expected."""
    ask = [{"role": "user", "content": PROBE}]
    plain = _render(tok, ask, enable_thinking)
    user_marker = plain.split(PROBE)[0]
    generation = _render(tok, ask, enable_thinking, generation=True)[len(plain):]
    history = _render(tok, ask + [{"role": "assistant", "content": PROBE + PROBE}], enable_thinking)
    in_history = history[len(plain):].split(PROBE + PROBE)[0]
    assistant_marker = _common_prefix(generation, in_history)
    two_turns = _render(tok, ask + [{"role": "assistant", "content": "ok"}, {"role": "user", "content": PROBE}], enable_thinking)
    if not user_marker or not assistant_marker or two_turns.count(user_marker) != 2 or assistant_marker not in two_turns:
        raise ValueError(f"cannot find the user/assistant markers in the chat template (user={user_marker!r}, assistant={assistant_marker!r})")
    return user_marker, assistant_marker


def token_count(tok, text: str) -> int:
    return len(tok(text, add_special_tokens=False)["input_ids"])


def render_file(path: str, tok, max_len: int, enable_thinking: bool) -> tuple[list[str], dict]:
    """(texts that fit max_len tokens, stats). Lines that cannot be rendered or are too long are counted, never silently lost."""
    texts, stats, longest = [], {"lines": 0, "kept": 0, "too_long": 0, "unreadable": 0, "max_tokens": 0}, 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            stats["lines"] += 1
            try:
                item = json.loads(line)
                text = _render(tok, item["messages"], enable_thinking, item.get("tools") or None)
                size = token_count(tok, text)
            except (ValueError, KeyError, TypeError, IndexError):
                stats["unreadable"] += 1
                continue
            longest = max(longest, size)
            if size > max_len:
                stats["too_long"] += 1
                continue
            texts.append(text)
            stats["kept"] += 1
    stats["max_tokens"] = longest
    return texts, stats


def write_stats(stats: dict, directory: str) -> str:
    path = os.path.join(directory, "render_stats.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=4)
    return path
