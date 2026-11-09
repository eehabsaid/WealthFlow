"""What every tool gets: project, settings, index, ledger, approver, plan scope, and the shas of files the model has read."""

from __future__ import annotations

from dataclasses import dataclass, field

from ai.dev_agent.engine.cancel import CancelToken
from ai.dev_agent.guard import paths


class DenyAll:
    """Default approver (non-interactive runs): nothing that needs the owner's approval is ever approved."""

    def ask(self, kind: str, message: str) -> bool:
        return False


@dataclass
class ToolContext:
    project: object
    settings: dict
    index: object
    ledger: object = None
    approver: object = field(default_factory=DenyAll)
    scope: object = None
    readonly: bool = True
    package: str = ""
    seen: dict = field(default_factory=dict)
    approved: set = field(default_factory=set)
    emit: object = lambda event: None
    cancel: object = field(default_factory=CancelToken)
    attachments: object = None   # owner attachments (engine.attachments.Attachments), added to the first message of a phase

    def ask(self, kind: str, key: str, message: str) -> bool:
        """Ask the owner once per key; the answer is saved in the ledger."""
        if key in self.approved:
            return True
        ok = bool(self.approver.ask(kind, message))
        if ok:
            self.approved.add(key)
        if self.ledger:
            self.ledger.record_approval(kind, key, ok, message)
        return ok

    def allow_write(self, rel: str, op: str) -> tuple[bool, str]:
        decision = paths.check_write(self.project, rel, op, self.scope)
        if decision.action == "allow":
            return True, ""
        if decision.action == "deny":
            return False, decision.reason
        if self.ask("write", f"write:{rel}", decision.reason):
            return True, ""
        return False, f"the owner did not approve: {decision.reason}. If it is a protected file, describe the fix with note_proposal instead."
