"""The agent: plan (read-only investigation) -> owner approves once -> execute work packages from the ledger -> verify and fix -> report."""

from __future__ import annotations

from ai.dev_agent.core import context
from ai.dev_agent.core.index import Index
from ai.dev_agent.ledger import plan as planlib
from ai.dev_agent.ledger.ledger import Ledger
from ai.dev_agent.memory.capture import capture
from ai.dev_agent.tools import DenyAll, ToolContext
from ai.dev_agent.engine import packages, recovery, report, runlock
from ai.dev_agent.engine.attachments import Attachments, AttachmentError
from ai.dev_agent.engine.cancel import CancelToken
from ai.dev_agent.engine.fix import verify_and_fix
from ai.dev_agent.engine.intent import FAILED, refuse, wrote_files
from ai.dev_agent.engine.protocol import PLAN_FORMAT, system_prompt
from ai.dev_agent.engine.session import run_phase


class AgentError(RuntimeError):
    pass


def _finished(ledger: Ledger) -> Ledger:
    capture(ledger)   # what happened goes into the repo memory (never raises)
    return ledger


class Agent:
    def __init__(self, project, provider, settings: dict, approver=None, emit=None, cancel=None, events: bool = False):
        """`events=True` (the command line) also writes every event, trace events included, to tasks/<id>/events.jsonl; the server does that itself."""
        self.project, self.provider, self.settings = project, provider, settings
        self.approver, self.emit = approver or DenyAll(), emit or (lambda event: None)
        self._emit_base, self._events, self._logs = self.emit, events, {}
        self.cancel = cancel or CancelToken()
        self.index = Index(project)

    def _ctx(self, ledger: Ledger, readonly: bool, scope=None, package: str = "") -> ToolContext:
        try:
            attachments = Attachments.load(ledger)
        except AttachmentError as exc:
            raise AgentError(str(exc)) from exc
        return ToolContext(self.project, self.settings, self.index, ledger, self.approver, scope, readonly, package, {}, ledger.approved_keys(), self.emit, self.cancel, attachments)

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
            first = f"TASK: {task}\n\n{background}\n\n{PLAN_FORMAT}{fix}"
            res = run_phase(ctx, self.provider, system_prompt(True), first, {"plan", "final"}, self.settings["max_steps_per_package"], label="plan")
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
        pkgs = packages.split(self.project, plan, self.settings["context_window"], self.settings["reserve_tokens"])
        ledger.data.update(plan=plan, plan_sha=planlib.digest(plan), packages=pkgs)
        ledger.set_status("awaiting_approval")
        return ledger

    def approve(self, task_id: str) -> Ledger:
        ledger = self._load(task_id)
        if ledger.data["status"] != "awaiting_approval" or not ledger.data["plan"]:
            raise AgentError(f"task {task_id} has no plan waiting for approval (status: {ledger.data['status']})")
        ledger.data["approved_at"] = ledger.data["updated"]
        ledger.set_status("approved")
        return ledger

    def execute(self, task_id: str) -> Ledger:
        ledger = self._load(task_id)
        try:
            with runlock.hold(ledger):
                if ledger.data["status"] == "executing":   # we hold the lock, so the run that left it "executing" died: make the ledger match the disk
                    recovery.recover_task(ledger)
                return _finished(self._execute(ledger))
        except runlock.TaskBusy as exc:
            raise AgentError(str(exc)) from exc

    def _execute(self, ledger: Ledger) -> Ledger:
        task_id, d = ledger.id, ledger.data
        if not d["approved_at"] or not d["plan"] or d["status"] not in ("approved", "executing", "stopped"):
            raise AgentError(f"task {task_id} is not approved (status: {d['status']})")
        if planlib.digest(d["plan"]) != d["plan_sha"]:
            raise AgentError("the plan was changed after it was shown to you; plan again")
        scope = planlib.PlanScope(d["plan"])
        ledger.set_status("executing")
        for pkg in d["packages"]:
            if pkg["status"] == "done":
                continue   # resume: finished packages are never repeated
            if self.cancel.is_set():
                return self._stop(ledger, pkg, self.cancel.reason)
            ctx = self._ctx(ledger, False, planlib.PlanScope(d["plan"], d["packages"], pkg["id"]), pkg["id"])   # this package's own files only
            self.emit({"type": "package", "id": pkg["id"], "title": pkg["title"], "status": "running"})
            resumed = pkg["status"] == "interrupted"
            pkg["status"] = "running"
            task = (f"{ledger.brief(pkg['id'])}\n\nDo ONLY the steps of package {pkg['id']}: {', '.join(pkg['steps'])}. Files: {', '.join(pkg['files'])}. Files that belong only to other packages are refused.\n"
                    "When finished, reply {\"final\": \"what you changed and what you did not check\"}." + (f"\n\n{recovery.NOTE}" if resumed else ""))
            res = run_phase(ctx, self.provider, system_prompt(False), task, {"final"}, self.settings["max_steps_per_package"], label=f"package {pkg['id']}")
            if res.kind == "stopped":
                return self._stop(ledger, pkg, res.reason)
            pkg["summary"] = str(res.payload)[:400]
            d["agent_summaries"].append({"package": pkg["id"], "text": str(res.payload)[:500]})
            ok, why = verify_and_fix(ctx, self.provider, pkg["id"], lambda: ledger.changed_files())
            if not ok:
                return self._stop(ledger, pkg, why)
            pkg["status"] = "done"
            ledger.save()
            self.emit({"type": "package", "id": pkg["id"], "title": pkg["title"], "status": "done"})
        ctx = self._ctx(ledger, False, scope, "final")
        self.emit({"type": "phase", "phase": "final checks"})
        ok, why = verify_and_fix(ctx, self.provider, "final", lambda: ledger.changed_files())
        ledger.freeze_result_diffs()   # fixed now, before any later task can touch the same files
        if ok and not wrote_files(ledger):   # approved and "verified", yet no file was changed: that is not DONE
            ok, why = False, "FAILED: the plan was approved but no file was changed"
        ledger.set_status("completed" if ok else "stopped", why)
        report.write(ledger)
        return ledger

    def _stop(self, ledger: Ledger, pkg: dict, reason: str) -> Ledger:
        pkg["status"] = "stopped"
        ledger.set_status("stopped", f"{pkg['id']}: {reason}")
        report.write(ledger)
        return ledger
