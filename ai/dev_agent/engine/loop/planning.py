"""Planning half of the agent: plan, approve, run-if-auto."""

from __future__ import annotations

from ai.dev_agent.core import context
from ai.dev_agent.ledger import plan as planlib
from ai.dev_agent.ledger.ledger import Ledger
from ai.dev_agent.engine import packages, report, runlock
from ai.dev_agent.engine.intent import FAILED, refuse
from ai.dev_agent.engine.protocol import PLAN_FORMAT, PLAN_FORMAT_NATIVE, QUICK
from ai.dev_agent.engine.session import run_phase
from .support import AgentError, _finished


class _PlanningMixin:
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
