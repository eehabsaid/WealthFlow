"""run_phase: one model conversation."""

from __future__ import annotations


from ai.dev_agent.engine.attachments import AttachmentError
from ai.dev_agent.engine.trace import Trace
from .conversation import _Conversation
from .results import PhaseResult


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
