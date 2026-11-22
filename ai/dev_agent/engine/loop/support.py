"""Agent error, ledger finishing helper and the completion veto."""

from __future__ import annotations

from ai.dev_agent.ledger.ledger import Ledger
from ai.dev_agent.memory.capture import capture
from ai.dev_agent.engine.intent import FAILED, NO_CHANGE, evidence_ok, claims_change, is_stub, needs_changes, wrote_files


class AgentError(RuntimeError):
    pass


def _finished(ledger: Ledger) -> Ledger:
    capture(ledger)   # what happened goes into the repo memory (never raises)
    return ledger


class _Veto:
    """Refuses a final answer that is only words: a promise to read, or "done" for a change task with no file changed (engine/intent.py)."""

    def __init__(self, project, ledger, task: str):
        self.project, self.ledger, self.task = project, ledger, task

    def __call__(self, answer: str) -> str:
        from ai.dev_agent.engine.intent import NO_READ
        if is_stub(answer):
            return NO_READ
        if not wrote_files(self.ledger) and (needs_changes(self.task) or claims_change(answer)) and not evidence_ok(self.project, answer):
            return NO_CHANGE
        return ""

    @staticmethod
    def failed(why: str) -> str:
        return FAILED.get(why, why)
