"""One model conversation (a phase): the model calls tools, sees the (clipped) results and goes on until it answers without a tool call (or `submit_plan` while planning).
Native tool calling (Ollama, Anthropic, OpenAI, Gemini tools APIs) is the normal path; a model that writes its call as JSON text still works (text protocol), and a server
that has no tools API is switched to it automatically. Malformed output never ends the run: the problem is fed back to the model, up to a few times in a row.
Guards against loops: the same call repeated, a step limit, the context budget (engine/budget.py)."""

from __future__ import annotations

import json
from dataclasses import dataclass

from ai.dev_agent.core import rules as rulelib
from ai.dev_agent.engine import meter, protocol
from ai.dev_agent.engine.attachments import AttachmentError
from ai.dev_agent.engine.budget import Budget, ContextOverflow, clip_text, tokens
from ai.dev_agent.engine.cancel import Cancelled
from ai.dev_agent.engine.trace import Trace, succeeded
from ai.dev_agent.providers.base import MalformedOutput, NoToolSupport, ProviderError
from ai.dev_agent.providers.toolmsg import new_id, to_text
from ai.dev_agent.tools import call, limits, native_specs

MAX_INVALID_TEXT, MAX_INVALID_NATIVE = 3, 5   # replies in a row that cannot be used before the phase stops
MAX_CALLS_PER_REPLY = 8
LENGTH_STOPS = {"length", "max_tokens", "max_output_tokens", "max_tokens_reached", "max_tokens_exceeded"}


@dataclass
class PhaseResult:
    kind: str                 # "final" | "plan" | "stopped"
    payload: object = None
    reason: str = ""
    messages: list | None = None   # the conversation at the end, so the next phase (fixing failed checks) can continue it


def _brief(args) -> str:
    text = json.dumps(args, ensure_ascii=False, default=str)
    return text if len(text) <= 240 else text[:237] + "..."


def _summary(name: str, result: dict) -> str:
    """One short line for the live feed (never file contents). An empty `error` (edit_files has the key even when all went well) is not an error."""
    if result.get("error"):
        return str(result["error"])[:240]
    if name == "edit_files":
        return ", ".join(f"{f['path']}: {f['state']}" for f in result.get("files", []))[:240]
    if name in ("edit_file", "write_file"):
        return f"{result.get('path')}: {result.get('state')}"
    if name in ("run_command", "git", "run_tests", "shell"):
        return f"{result.get('status')} (exit {result.get('exit_code')}, {result.get('duration_s')}s)" + (f", changed {len(result['files_changed'])} file(s)" if result.get("files_changed") else "")
    if name == "read_file":
        return f"{result.get('path')} lines {result.get('start')}-{result.get('end')} of {result.get('total_lines')}"
    if name in ("grep", "search_index", "web_search"):
        return f"{len(result.get('matches') or result.get('results') or [])} results"
    if name in ("glob", "list_dir"):
        return f"{len(result.get('files') or result.get('entries') or [])} entries"
    if name == "web_fetch":
        return f"{result.get('url')} ({len(result.get('text') or '')} chars)"
    if name == "todo":
        return f"{result.get('open')} open of {len(result.get('items') or [])}"
    return "ok"


def run_phase(ctx, provider, system, first_user: str, accept: set[str], max_steps: int, attach: bool = True, label: str = "", history: list | None = None, veto=None) -> PhaseResult:
    """One conversation. `system` = None builds the normal system prompt (native or text protocol, plus the project's AGENTS.md rules); a string is used as it is.
    `history` = the messages of an earlier phase to continue (the model keeps what it learned; `first_user` is added as a new user message). `veto(text) -> str`: called with
    a final answer; a non-empty string is sent back to the model instead of ending the phase (at most 3 times, then the phase stops with that text as the reason).
    Besides the live feed it writes the phase's full trace (engine/trace.py) and, after every model call, a `context` event with the real token usage (engine/meter.py)."""
    trace = Trace(ctx, provider, label)
    first = {"role": "user", "content": first_user}
    if attach and getattr(ctx, "attachments", None):
        try:
            first = ctx.attachments.message(first_user, provider.has_vision())
        except AttachmentError as exc:
            return PhaseResult("stopped", reason=str(exc))
    conv = _Conversation(ctx, provider, system, first, accept, max_steps, trace, label, history, veto)
    trace.start(conv.system, first)
    if history:
        trace.exact = False   # the logged first message is not the whole conversation any more
    result = conv.run()
    result.messages = conv.messages
    trace.end(trace.step, result.kind, result.reason)
    return result


def _context_event(ctx, trace, budget, system, messages, reply, label: str) -> None:
    estimate = budget.used(system, messages) + tokens(reply.text)   # messages do not hold the reply yet
    usage = reply.usage or {}
    snap = meter.snapshot(usage.get("input_tokens", 0), usage.get("output_tokens", 0), estimate, budget.window, budget.reserve)
    ctx.emit({"type": "context", "phase": label or "phase", "step": trace.step, **snap})
    trace.model(trace.step, reply, estimate)


class _Conversation:
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

    def _handle(self, step: int, reply) -> PhaseResult | None:
        finish = (getattr(reply, "finish_reason", "") or "").strip().lower()
        calls = list(getattr(reply, "tool_calls", None) or [])
        if finish in LENGTH_STOPS and not calls:   # the reply was cut at the output limit: a half-written call is useless
            if self.ctx.ledger:
                self.ctx.ledger.event("truncated_reply", finish_reason=finish, chars=len(reply.text), output_tokens=(reply.usage or {}).get("output_tokens", 0),
                                      text=reply.text[:1500], tail=reply.text[-1500:])
            self.messages.append({"role": "assistant", "content": reply.text[:2000] + ("..." if len(reply.text) > 2000 else "")})
            return self._bad_reply(step, reply, f"truncated at {finish}", "Your last reply was cut off at the output limit, so nothing was run. Send a much smaller call: edit one part at a time, write a large file in chunks, read ranges instead of whole files.",
                                   f"provider stopped generation at its output limit ({finish}) {{n}} times in a row; increase max_output_tokens or reduce the tool-call payload")
        action = None
        if not calls:
            action = protocol.parse_reply(reply.text)
            if action.kind == "tool":
                calls = [{"id": new_id(), "name": action.payload[0], "args": action.payload[1]}]
            elif action.kind == "invalid" and self.native and reply.text.strip() and not protocol.looks_like_call(reply.text):
                action = protocol.Action("final", reply.text.strip())   # plain prose from a native-tool-calling model = its answer
        self.messages.append({"role": "assistant", "content": reply.text, **({"tool_calls": calls} if calls and self.native else {})})
        if not calls:
            if action.kind == "invalid":
                note = str(action.payload)
                return self._bad_reply(step, reply, note, protocol.nudge_for(action, self.native), "the model gave {n} replies in a row that were not valid tool calls or answers (" + note.replace("{", "(").replace("}", ")") + ")")
            self.invalid = 0
            if action.kind in self.accept:
                if action.kind == "final" and self.used_todo and self._open_todos() and not self.todo_nudged and not self.ctx.readonly:   # only a checklist the model wrote itself
                    self.todo_nudged = True
                    self._say(step, "open_todos", f"Your checklist still has open items: {self._open_todos()}. Finish them, or mark them done with todo, then answer.")
                    return None
                if action.kind == "final" and self.veto and (why := self.veto(str(action.payload))):
                    self.vetoed += 1
                    if self.vetoed >= 3:
                        return PhaseResult("stopped", reason=self.veto.failed(why) if hasattr(self.veto, "failed") else why)
                    if self.ctx.ledger:
                        self.ctx.ledger.event("refused_final_answer", text=str(action.payload)[:500])
                    self._say(step, "final_refused", why)
                    return None
                return PhaseResult(action.kind, action.payload)
            self._say(step, "reply_not_accepted", f"A '{action.kind}' reply is not accepted in this phase. Use a tool or reply with {sorted(self.accept)}.")
            return None
        self.invalid = 0
        return self._run_calls(step, calls, reply)

    def _open_todos(self) -> str:
        items = (self.ctx.ledger.data.get("todos") if self.ctx.ledger else None) or []
        return "; ".join(i["text"] for i in items if i["status"] != "done")[:300]

    def _run_calls(self, step: int, calls: list[dict], reply) -> PhaseResult | None:
        ctx, s = self.ctx, self.ctx.settings
        for index, item in enumerate(calls):   # every call needs a result message (the APIs require it), even one that is not run
            name, args, call_id = item["name"], item["args"], item["id"]
            if index >= MAX_CALLS_PER_REPLY:
                self._results_append(call_id, name, f"TOOL RESULT {name}:\nnot run: at most {MAX_CALLS_PER_REPLY} calls per reply; send it again")
                continue
            if name == "submit_plan" and "plan" in self.accept:
                for later in calls[index:]:
                    self._results_append(later["id"], later["name"], "TOOL RESULT submit_plan:\nplan received")
                return PhaseResult("plan", args)
            key = name + json.dumps(args, sort_keys=True, default=str)
            self.repeats = self.repeats + 1 if key == self.last_key else 1
            self.last_key = key
            stop_at = limits.of(s)["repeat_stop"]
            if self.repeats >= stop_at:
                return PhaseResult("stopped", reason=f"the model repeated the same call to {name} {stop_at} times in a row")
            if self.repeats == stop_at - 1:
                warn = f"TOOL RESULT {name}:\nYou already made this exact call {self.repeats - 1} times. Change approach or finish."
                self._results_append(call_id, name, warn)
                self.trace.message(step, "repeat_warning", warn)
                continue
            if ctx.cancel.is_set():
                self._results_append(call_id, name, f"TOOL RESULT {name}:\nnot run: the task was stopped")
                continue
            result = call(ctx, name, args)
            self.used_todo = self.used_todo or (name == "todo" and not result.get("error"))
            ctx.emit({"type": "tool", "name": name, "ok": succeeded(result), "args": _brief(args), "summary": _summary(name, result)})
            content = f"TOOL RESULT {name}:\n" + clip_text(json.dumps(result, ensure_ascii=False, default=str), s["max_tool_result_chars"] * limits.of(s)["result_factor"])
            self._results_append(call_id, name, content)
            self.trace.tool(step, name, args, result, content)
        return None


class _Empty:
    text, usage, finish_reason = "", {}, ""
