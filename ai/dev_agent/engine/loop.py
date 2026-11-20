"""The agent. Two ways in, one loop:
  - plan approval ON (default): read-only investigation -> plan -> the owner approves once -> the work loop (tools until done) -> checks and fixes -> report.
  - plan approval OFF (Settings > Behavior): no planning phase; the work loop starts at once and the owner is asked only before risky actions (guard/*).
The work loop is engine/session.py: the model calls tools and reads their results until it answers; then the project's checks run and failures go back to the same
conversation (at most 3 failed fix attempts on the same error)."""

from __future__ import annotations

from ai.dev_agent.core import context
from ai.dev_agent.core.index import Index
from ai.dev_agent.ledger import plan as planlib
from ai.dev_agent.ledger.ledger import Ledger
from ai.dev_agent.memory.capture import capture
from ai.dev_agent.tools import DenyAll, ToolContext, plugins
from ai.dev_agent.engine import packages, recovery, report, runlock
from ai.dev_agent.engine.attachments import Attachments, AttachmentError
from ai.dev_agent.engine.cancel import CancelToken
from ai.dev_agent.engine.fix import verify_and_fix
from ai.dev_agent.engine.intent import FAILED, NO_CHANGE, evidence_ok, claims_change, is_stub, needs_changes, refuse, wrote_files
from ai.dev_agent.engine.protocol import FINISH_NATIVE, FINISH_TEXT, PLAN_FORMAT, PLAN_FORMAT_NATIVE, QUICK
from ai.dev_agent.engine.session import run_phase


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


class Agent:
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

    # ---- planning ----
    def plan(self, task: str, ledger: Ledger | None = None) -> Ledger:
        """Investigate read-only and propose a plan. `ledger` lets a UI create the task first so it knows the task id at once."""
        ledger = ledger or Ledger.create(self.project, task)
        self._tee(ledger)
        ledger.listener = self.emit
        try:
            with runlock.hold(ledger):
                return _finished(self._plan(task, ledger))
        except runlock.TaskBusy as exc:
            raise AgentError(str(exc)) from exc

    def _plan(self, task: str, ledger: Ledger) -> Ledger:
        self.emit({"type": "phase", "phase": "planning"})
        ctx = self._ctx(ledger, True)
        background = context.render(context.pick(self.project, self.index, task))
        problems: list[str] = []
        for attempt in range(3):
            fix = "\n\nYour previous plan was rejected:\n- " + "\n- ".join(problems) if problems else ""
            quick = QUICK if self.settings.get("quick_mode") else ""
            first = f"{self._earlier(ledger)}TASK: {task}\n\n{background}\n\n{PLAN_FORMAT_NATIVE if self._native() else PLAN_FORMAT}{quick}{fix}"
            res = run_phase(ctx, self.provider, None, first, {"plan", "final"}, self.settings["max_steps_per_package"], label="plan")
            if res.kind == "stopped":
                ledger.set_status("stopped", res.reason)
                report.write(ledger)
                return ledger
            why = refuse(self.project, task, str(res.payload)) if res.kind == "final" else ""
            if why:   # a change request is never finished by words, nor a question by a promise to read: ask again, and fail after 3 attempts
                ledger.event("refused_final_answer", text=str(res.payload)[:500])
                problems = [why]
                continue
            if res.kind == "final":   # a question, or "no change needed" with checked evidence
                ledger.data["answer"] = str(res.payload)
                ledger.set_status("answered")
                report.write(ledger)
                return ledger
            plan, problems = planlib.validate(self.project, res.payload)
            if not problems:
                break
        else:
            ledger.set_status("stopped", (FAILED[problems[0]] if problems and problems[0] in FAILED
                                          else "no valid plan after 3 attempts: " + "; ".join(problems[:4])))
            report.write(ledger)
            return ledger
        ledger.data.update(plan=plan, plan_sha=planlib.digest(plan), packages=packages.single(plan))
        ledger.set_status("awaiting_approval")
        return ledger

    def run_if_auto(self, task_id: str) -> Ledger | None:
        """After planning: when the owner switched the plan approval off, approve and execute at once (recorded in the ledger). None = nothing done."""
        ledger = self._load(task_id)
        if not self.auto_approve or ledger.data["status"] != "awaiting_approval" or not ledger.data["plan"]:
            return None
        ledger.record_approval("plan", "plan", True, "approved automatically: the plan approval is switched off in Settings > Behavior")
        self.emit({"type": "phase", "phase": "plan approved automatically (Settings > Behavior)"})
        self.approve(task_id)
        return self.execute(task_id)

    def approve(self, task_id: str) -> Ledger:
        ledger = self._load(task_id)
        if ledger.data["status"] != "awaiting_approval" or not ledger.data["plan"]:
            raise AgentError(f"task {task_id} has no plan waiting for approval (status: {ledger.data['status']})")
        ledger.data["approved_at"] = ledger.data["updated"]
        ledger.set_status("approved")
        return ledger

    # ---- working ----
    def direct(self, task: str, ledger: Ledger) -> Ledger:
        """No planning phase: the task starts as an implicitly approved open plan (recorded in the ledger) and the work loop runs at once."""
        self._tee(ledger)
        ledger.listener = self.emit
        plan = planlib.direct_plan(task)
        ledger.data.update(plan=plan, plan_sha=planlib.digest(plan), packages=packages.single(plan))
        ledger.record_approval("plan", "plan", True, "no planning phase: plan approval is switched off in Settings > Behavior; risky actions still ask")
        ledger.data["approved_at"] = ledger.data["updated"]
        ledger.set_status("approved")
        return self.execute(ledger.id)

    def execute(self, task_id: str) -> Ledger:
        ledger = self._load(task_id)
        try:
            with runlock.hold(ledger):
                if ledger.data["status"] == "executing":   # we hold the lock, so the run that left it "executing" died: make the ledger match the disk
                    recovery.recover_task(ledger)
                return _finished(self._execute(ledger))
        except runlock.TaskBusy as exc:
            raise AgentError(str(exc)) from exc

    def _start_text(self, ledger: Ledger, resumed: bool) -> str:
        d, plan = ledger.data, ledger.data["plan"]
        finish = FINISH_NATIVE if self._native() else FINISH_TEXT
        if plan.get("direct"):
            background = context.render(context.pick(self.project, self.index, d["goal"]))
            quick = "\nThis is a small task: keep it short and direct." if self.settings.get("quick_mode") else ""
            body = f"{self._earlier(ledger)}TASK: {d['goal']}\n\n{background}{quick}\n\n{finish}"
        else:
            body = (f"{ledger.brief('P1')}\n\nCarry out the approved plan (every step). Files the plan does not list ask the owner again; deleting or renaming needs to be listed. {finish}")
        return body + (f"\n\n{recovery.NOTE}" if resumed else "")

    def _execute(self, ledger: Ledger) -> Ledger:
        task_id, d = ledger.id, ledger.data
        if not d["approved_at"] or not d["plan"] or d["status"] not in ("approved", "executing", "stopped"):
            raise AgentError(f"task {task_id} is not approved (status: {d['status']})")
        if planlib.digest(d["plan"]) != d["plan_sha"]:
            raise AgentError("the plan was changed after it was shown to you; plan again")
        scope = planlib.PlanScope(d["plan"])
        ledger.set_status("executing")
        pkg = d["packages"][0]
        if self.cancel.is_set():
            return self._stop(ledger, pkg, self.cancel.reason)
        ctx = self._ctx(ledger, False, scope, pkg["id"])
        if not d["plan"].get("direct") and not d.get("todos"):   # the plan's steps become the visible checklist; the model updates it with the todo tool
            d["todos"] = [{"text": s["title"], "status": "pending"} for s in d["plan"]["steps"]]
            ledger.save()
            self.emit({"type": "todo", "items": d["todos"]})
        self.emit({"type": "package", "id": pkg["id"], "title": pkg["title"], "status": "running"})
        resumed = pkg["status"] in ("interrupted", "stopped") or bool(d["files"])
        pkg["status"] = "running"
        veto = _Veto(self.project, ledger, d["goal"])
        res = run_phase(ctx, self.provider, None, self._start_text(ledger, resumed), {"final"}, self.settings["max_steps_per_package"], label=f"package {pkg['id']}", veto=veto)
        if res.kind == "stopped":
            return self._stop(ledger, pkg, res.reason)
        pkg["summary"] = str(res.payload)[:400]
        d["agent_summaries"].append({"package": pkg["id"], "text": str(res.payload)[:500]})
        if d["plan"].get("direct") and not wrote_files(ledger):   # a question, or a change task already satisfied (evidence checked): an answer, nothing to verify
            pkg["status"] = "done"
            d["answer"] = str(res.payload)
            ledger.set_status("answered")
            self.emit({"type": "package", "id": pkg["id"], "title": pkg["title"], "status": "done"})
            report.write(ledger)
            return ledger
        self.emit({"type": "phase", "phase": "final checks"})
        final_ctx = self._ctx(ledger, False, scope, "final")   # package "final": the once-per-task browser E2E runs here (engine/e2e.py)
        final_ctx.seen = ctx.seen   # what the model read or wrote stays known to its fix rounds (SHA checks)
        ok, why = verify_and_fix(final_ctx, self.provider, "final", lambda: ledger.changed_files(), res.messages)
        if not ok:
            return self._stop(ledger, pkg, why)
        pkg["status"] = "done"
        ledger.save()
        self.emit({"type": "package", "id": pkg["id"], "title": pkg["title"], "status": "done"})
        ledger.freeze_result_diffs()   # fixed now, before any later task can touch the same files
        if not wrote_files(ledger):   # approved and "verified", yet no file was changed: that is not DONE
            ledger.set_status("stopped", "FAILED: the plan was approved but no file was changed")
        else:
            ledger.set_status("completed")
        report.write(ledger)
        return ledger

    def _stop(self, ledger: Ledger, pkg: dict, reason: str) -> Ledger:
        pkg["status"] = "stopped"
        ledger.set_status("stopped", f"{pkg['id']}: {reason}")
        report.write(ledger)
        return ledger
