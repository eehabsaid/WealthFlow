"""Provider proxy: tells the model it CAN change the user's records (through a confirmation card) and draw charts.

Without it a model asked "add an expense of 50" or "change that expense to 60" tends to answer "I only have read-only access" and
never calls propose_action. Same idea as exports/notice.py: every pipeline calls provider.generate(messages, ...), so wrapping the
provider once covers the Ask and Agent paths alike."""

from __future__ import annotations

from typing import Any

NOTICE = (
    "CHANGING RECORDS: when the user asks to add, change or delete an expense, a reminder or a salary entry, you CAN do it: call the tool "
    "propose_action once. It only shows a confirmation card under your answer; nothing is saved until the user presses Confirm. "
    "For a change or a delete first find the record with a read tool, then pass its id (or date, amount and description) as `target`. "
    "For an expense also pass its `category` and `subcategory` when they are clear from the request, using the user's own category list (the tool answers with the valid names when one is unknown); the user can still change every value on the card. "
    "Never say you only have read-only access and never tell the user to do it by hand. Call it once per change: do not repeat the same card. "
    "CHARTS: when the user asks for a chart, call show_chart; never type chart numbers yourself."
)


class ActionNoticeProvider:
    def __init__(self, provider: Any):
        self._provider = provider

    def __getattr__(self, name: str) -> Any:
        return getattr(self._provider, name)

    def generate(self, messages: list[dict[str, Any]], *args: Any, **kwargs: Any) -> Any:
        messages = [dict(m) for m in messages or []]
        if messages and messages[0].get("role") == "system":
            messages[0]["content"] = f"{messages[0].get('content', '')}\n\n{NOTICE}"
        else:
            messages.insert(0, {"role": "system", "content": NOTICE})
        return self._provider.generate(messages, *args, **kwargs)
