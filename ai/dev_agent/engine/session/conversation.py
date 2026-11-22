"""The model conversation loop (one phase)."""

from __future__ import annotations


from ai.dev_agent.core import rules as rulelib
from ai.dev_agent.engine import protocol
from ai.dev_agent.engine.budget import Budget, ContextOverflow
from ai.dev_agent.engine.cancel import Cancelled
from ai.dev_agent.providers.base import MalformedOutput, NoToolSupport, ProviderError
from ai.dev_agent.providers.toolmsg import to_text
from ai.dev_agent.tools import native_specs
from .handling import _HandlingMixin
from .results import MAX_INVALID_NATIVE, MAX_INVALID_TEXT, PhaseResult, _Empty, _context_event


class _Conversation(_HandlingMixin):
    def __init__(self, ctx, provider, system, first, accept, max_steps, trace, label, history=None, veto=None):
        s = ctx.settings
        self.ctx, self.provider, self.accept, self.max_steps, self.trace, self.label = ctx, provider, accept, max_steps, trace, label
        self.fixed_system = system if isinstance(system, str) else None
        self.rules = "" if self.fixed_system is not None else rulelib.load(ctx.project)
        self.native = bool(getattr(provider, "native_tools", False)) and self.fixed_system is None
        self.system = self._system()
        self.budget, self.veto, self.vetoed = Budget(s["context_window"], s["reserve_tokens"]), veto, 0
        self.messages = [dict(m) for m in history] + [first] if history else [first]
        self.invalid, self.repeats, self.last_key, self.todo_nudged, self.used_todo = 0, 0, None, False, False

    # ---- pieces ----
    def _system(self) -> str:
        return self.fixed_system if self.fixed_system is not None else protocol.system_prompt(self.ctx.readonly, self.native, self.rules, self.ctx.hidden)

    def _tools(self):
        return native_specs(self.ctx.readonly, self.ctx.hidden) if self.native else None

    def _say(self, step: int, why: str, text: str) -> None:
        self.messages.append({"role": "user", "content": text})
        self.trace.message(step, why, text)

    def _bad_reply(self, step: int, reply, note: str, nudge: str, reason: str) -> PhaseResult | None:
        """An unusable reply: record it, tell the model what was wrong, and go on; stop only after several in a row."""
        ctx = self.ctx
        self.invalid += 1
        if ctx.ledger:
            ctx.ledger.event("invalid_reply", text=reply.text[:1500], tail=reply.text[-1500:], chars=len(reply.text), note=note[:200], finish_reason=getattr(reply, "finish_reason", "") or "")
        if self.invalid >= (MAX_INVALID_NATIVE if self.native else MAX_INVALID_TEXT):
            return PhaseResult("stopped", reason=reason.format(n=self.invalid))
        self._say(step, "invalid_reply_nudge", nudge)
        return None

    def _results_append(self, call_id: str, name: str, content: str) -> None:
        self.messages.append({"role": "tool", "tool_call_id": call_id, "name": name, "content": content} if self.native else {"role": "user", "content": content})

    def _switch_to_text(self, step: int, why: str) -> None:
        self.native = False
        try:
            self.provider.native_tools = False   # later phases of this run start in the text protocol straight away
        except AttributeError:
            pass
        self.messages[:] = to_text(self.messages)
        self.system = self._system()
        self.trace.message(step, "native_tools_unavailable", f"{why}; the plain-text JSON protocol is used from here")

    # ---- the loop ----
    def run(self) -> PhaseResult:
        ctx = self.ctx
        step = 0
        while step < self.max_steps:
            step += 1
            self.trace.step = step
            if ctx.cancel.is_set():
                return PhaseResult("stopped", reason=ctx.cancel.reason)
            try:
                touched = self.budget.compact(self.system, self.messages)
                if touched:
                    self.trace.compact(step, touched)
                reply = self._complete()
            except Cancelled:
                return PhaseResult("stopped", reason=ctx.cancel.reason or "stopped by user")
            except ContextOverflow as exc:
                return PhaseResult("stopped", reason=str(exc))
            except NoToolSupport as exc:
                self._switch_to_text(step, f"the model server has no tools API ({str(exc)[:120]})")
                step -= 1
                continue
            except MalformedOutput as exc:
                stop = self._bad_reply(step, _Empty(), str(exc), f"{exc}", "the model's output could not be decoded {n} times in a row (" + str(exc)[:200].replace("{", "(").replace("}", ")") + ")")
                if stop:
                    return stop
                continue
            except ProviderError as exc:
                return PhaseResult("stopped", reason=f"provider error: {exc}")
            if ctx.ledger:
                ctx.ledger.add_usage(reply.usage)
            _context_event(ctx, self.trace, self.budget, self.system, self.messages, reply, self.label)
            done = self._handle(step, reply)
            if done:
                return done
        return PhaseResult("stopped", reason=f"step limit ({self.max_steps}) reached")

    def _complete(self):
        tools = self._tools()
        if tools is None:
            return self.provider.complete(self.system, self.messages, cancel=self.ctx.cancel)
        return self.provider.complete(self.system, self.messages, cancel=self.ctx.cancel, tools=tools)
