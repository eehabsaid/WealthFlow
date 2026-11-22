"""Reply handling and tool-call running for a conversation."""

from __future__ import annotations

import json

from ai.dev_agent.engine import protocol
from ai.dev_agent.engine.budget import clip_text
from ai.dev_agent.engine.trace import succeeded
from ai.dev_agent.providers.toolmsg import new_id
from ai.dev_agent.tools import call, limits
from .results import LENGTH_STOPS, MAX_CALLS_PER_REPLY, PhaseResult, _brief, _summary


class _HandlingMixin:
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
