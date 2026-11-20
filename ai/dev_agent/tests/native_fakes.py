"""A scripted model that speaks the native tool-calling API: each reply is a Reply with tool_calls, plain text, or an exception to raise."""

from __future__ import annotations

from ai.dev_agent.providers.base import Provider, ProviderError, Reply


class Native(Provider):
    name = "native-fake"
    native_tools = True

    def __init__(self, replies):
        super().__init__("fake", "http://localhost")
        self.replies, self.calls = list(replies), []

    def complete(self, system, messages, cancel=None, tools=None):
        self.calls.append({"system": system, "messages": [dict(m) for m in messages], "tools": tools})
        if not self.replies:
            raise ProviderError("scripted model has no more replies")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def call(*pairs, text: str = "") -> Reply:
    """call(("read_file", {"path": "a.py"}), ("grep", {...})) -> a reply with those native tool calls."""
    return Reply(text, {"input_tokens": 10, "output_tokens": 5}, "tool_calls", {}, [{"id": f"c{i}", "name": n, "args": a} for i, (n, a) in enumerate(pairs, 1)])


def say(text: str) -> Reply:
    return Reply(text, {"input_tokens": 10, "output_tokens": 5}, "stop")
