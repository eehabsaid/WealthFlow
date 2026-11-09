"""History-window selection for assemble_messages (split out for the 200-line rule)."""

from __future__ import annotations

from typing import Any, Callable, Sequence


def select_history(history_messages: Sequence[Any] | None, budget_tokens: int,
                   estimate: Callable[[str], int]) -> list[dict[str, str]]:
    """Newest-first fill of the remaining token budget; returns oldest-first messages."""
    out: list[dict[str, str]] = []
    if not history_messages or budget_tokens <= 100:
        return out
    used = 0
    for msg in reversed(list(history_messages)):
        t = estimate(f"{msg.role}: {msg.content}")
        if used + t > budget_tokens:
            break
        used += t
        out.insert(0, {"role": msg.role, "content": msg.content})
    return out
