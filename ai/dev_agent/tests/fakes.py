"""Scripted fake model and approver: the model answers from a prepared list, so the whole engine is tested without a real LLM."""

from __future__ import annotations

import json

from ai.dev_agent.providers.base import Provider, ProviderError, Reply


class Scripted(Provider):
    name = "scripted"

    def __init__(self, replies):
        super().__init__("fake", "http://localhost")
        self.replies, self.calls = list(replies), []

    def complete(self, system, messages, cancel=None):
        self.calls.append((system, [dict(m) for m in messages]))
        if not self.replies:
            raise ProviderError("scripted model has no more replies")
        reply = self.replies.pop(0)
        return Reply(reply(messages) if callable(reply) else reply, {"input_tokens": 10, "output_tokens": 5})


class Approver:
    def __init__(self, answer=False):
        self.answer, self.asked = answer, []

    def ask(self, kind, message):
        self.asked.append((kind, message))
        return self.answer(kind, message) if callable(self.answer) else self.answer


def tool(name, **args) -> str:
    return json.dumps({"tool": name, "args": args})


def final(text="done") -> str:
    return json.dumps({"final": text})


def plan(steps=None, **kw) -> str:
    body = {"summary": "test plan", "steps": steps or [{"title": "do it", "files": ["app/calc.py"]}], "files_add": [], "files_edit": ["app/calc.py"],
            "files_delete": [], "files_rename": [], "tests": [], "risks": [], **kw}
    return json.dumps({"plan": body})


def edit(*edits) -> str:
    return tool("edit_files", edits=list(edits))


class Blocking(Provider):
    """Answers the scripted replies, then waits like a model that is still generating until Stop cuts it off."""
    name = "blocking"

    def __init__(self, replies=()):
        super().__init__("fake", "http://localhost")
        self.replies, self.started = list(replies), __import__("threading").Event()

    def complete(self, system, messages, cancel=None):
        if self.replies:
            return Reply(self.replies.pop(0), {"input_tokens": 1, "output_tokens": 1})
        self.started.set()
        if cancel is not None and cancel.wait(30):
            from ai.dev_agent.engine.cancel import Cancelled
            raise Cancelled(cancel.reason)
        raise ProviderError("blocking model timed out")
