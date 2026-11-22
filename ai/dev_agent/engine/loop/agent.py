"""The Agent: construction and entry points."""

from __future__ import annotations

from ai.dev_agent.core.index import Index
from ai.dev_agent.ledger.ledger import Ledger
from ai.dev_agent.tools import DenyAll, ToolContext, plugins
from ai.dev_agent.engine.attachments import Attachments, AttachmentError
from ai.dev_agent.engine.cancel import CancelToken
from .support import AgentError
from .planning import _PlanningMixin
from .working import _WorkingMixin


class Agent(_PlanningMixin, _WorkingMixin):
    def __init__(self, project, provider, settings: dict, approver=None, emit=None, cancel=None, events: bool = False):
        """`events=True` (the command line) also writes every event, trace events included, to tasks/<id>/events.jsonl; the server does that itself."""
        self.project, self.provider, self.settings = project, provider, settings
        self.approver, self.emit = approver or DenyAll(), emit or (lambda event: None)
        self._emit_base, self._events, self._logs = self.emit, events, {}
        self.cancel = cancel or CancelToken()
        self.index = Index(project)
        for problem in plugins.load(project):   # tool plugins (config `tool_modules`, coding_agent/tools/*.py); a broken one is reported, never fatal
            self.emit({"type": "warning", "message": problem})

    def _ctx(self, ledger: Ledger, readonly: bool, scope=None, package: str = "") -> ToolContext:
        try:
            attachments = Attachments.load(ledger)
        except AttachmentError as exc:
            raise AgentError(str(exc)) from exc
        return ToolContext(self.project, self.settings, self.index, ledger, self.approver, scope, readonly, package, {}, ledger.approved_keys(), self.emit, self.cancel, attachments, self.provider)

    def _tee(self, ledger: Ledger) -> None:
        if not self._events:
            return
        from ai.dev_agent.service.events import EventLog

        log = self._logs.setdefault(ledger.id, EventLog(ledger.dir / "events.jsonl"))
        self.emit = lambda event: (log.append(event), self._emit_base(event))[1]

    def _load(self, task_id: str) -> Ledger:
        ledger = Ledger.load(self.project, task_id)
        self._tee(ledger)
        ledger.listener = self.emit   # ledger events (status changes, invalid replies) reach the live feed too
        return ledger

    def _native(self) -> bool:
        return bool(getattr(self.provider, "native_tools", False))

    def _earlier(self, ledger: Ledger) -> str:
        earlier = ledger.data.get("chat_context") or ""
        return f"EARLIER IN THIS CHAT (the owner continues the same conversation; build on it, do not redo it):\n{earlier}\n\n" if earlier else ""

    # ---- entry point for the interfaces ----
    def start(self, task: str, ledger: Ledger | None = None) -> Ledger:
        """What every interface calls for a new task: plan approval ON -> plan (the owner approves, then `execute`); OFF -> work at once."""
        ledger = ledger or Ledger.create(self.project, task)
        if self.auto_approve:
            return self.direct(task, ledger)
        return self.plan(task, ledger)

    @property
    def auto_approve(self) -> bool:
        """Settings > Behavior: only the plan-approval switch decides (quick mode never approves for you)."""
        return not self.settings.get("require_plan_approval", True)
