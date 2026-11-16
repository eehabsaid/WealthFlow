"""The full trajectory of a phase, written to the task's events.jsonl as `trace` events so a complete multi-turn conversation can be exported later.

A phase is one model conversation: system prompt + a first user message, then (assistant JSON reply, user "TOOL RESULT ..." message) pairs until the
model answers `final` or `plan`. Per phase this records, all passed through the redactor (secrets, emails, phone numbers, currency amounts):
  phase_start  the exact system prompt, the first message, and how the provider is called (format, num_ctx, num_predict)
  model        the model's own reply text exactly as received, its token usage, finish reason and the provider's raw message
  tool_result  the tool, its arguments, the FULL result, and `message`: the exact text sent back to the model (the result after clipping)
  message      any other message the loop added (invalid-reply nudge, repeat warning)
  compact      the loop trimmed old steps to fit the window; later messages are then no longer the full history (`exact` false)
  phase_end    how it ended (final / plan / stopped) and why
Messages are listed in the order they were appended to the conversation; the request the provider got is [system] + messages (roles merged)."""

from __future__ import annotations

import json

from ai.dev_agent.core import redact

CAP = 100_000   # characters kept per logged text; the model itself never saw more than max_tool_result_chars of a result


def _text(value: str) -> tuple[str, int, bool]:
    clean, hits = redact.redact(value)
    return (clean[:CAP], hits, len(clean) > CAP)


def _result(value) -> tuple[object, int]:
    clean, hits = redact.redact_value(value)
    raw = json.dumps(clean, ensure_ascii=False, default=str)
    return (clean if len(raw) <= CAP else {"truncated": True, "text": raw[:CAP]}), hits


def _ok(result: dict) -> bool:
    """A tool succeeded when it says so (`ok`), else when it carries no error. (edit_files always has an `error` key, empty when all went well.)"""
    return bool(result["ok"]) if "ok" in result else not result.get("error")


class Trace:
    def __init__(self, ctx, provider, label: str):
        self.ctx, self.provider, self.label, self.exact, self.step = ctx, provider, label or "phase", True, 0

    def _emit(self, kind: str, step: int = 0, **data) -> None:
        self.ctx.emit({"type": "trace", "kind": kind, "phase": self.label, "step": step, **data})

    def start(self, system: str, first: dict) -> None:
        sys_text, h1, _ = _text(system)
        user, h2, cut = _text(first["content"])
        meta = getattr(self.provider, "request_meta", None)
        self._emit("phase_start", system=sys_text, messages=[{"role": "user", "content": user}], images=len(first.get("images", ())),
                   request=meta() if callable(meta) else {}, redactions=h1 + h2, truncated=cut)

    def model(self, step: int, reply, estimate: int) -> None:
        text, hits, cut = _text(reply.text)
        raw, h2 = _result(getattr(reply, "raw", None) or {})
        self._emit("model", step, reply=text, usage=reply.usage, finish_reason=reply.finish_reason, raw=raw, estimate=estimate, redactions=hits + h2, truncated=cut,
                   exact=self.exact)

    def tool(self, step: int, name: str, args, result: dict, message: str) -> None:
        full, h1 = _result(result)
        sent, h2, cut = _text(message)
        clean_args, h3 = _result(args)
        self._emit("tool_result", step, tool=name, args=clean_args, ok=_ok(result), result=full, message=sent, redactions=h1 + h2 + h3, truncated=cut)

    def message(self, step: int, why: str, content: str) -> None:
        text, hits, _ = _text(content)
        self._emit("message", step, why=why, message=text, redactions=hits)

    def compact(self, step: int, touched: int) -> None:
        self.exact = False
        self._emit("compact", step, touched=touched)

    def end(self, step: int, kind: str, reason: str = "") -> None:
        self._emit("phase_end", step, result=kind, reason=reason[:500], exact=self.exact)
