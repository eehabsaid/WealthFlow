"""Working half of the agent: direct, execute and stop."""

from __future__ import annotations

from ai.dev_agent.core import context
from ai.dev_agent.ledger import plan as planlib
from ai.dev_agent.ledger.ledger import Ledger
from ai.dev_agent.engine import packages, recovery, report, runlock
from ai.dev_agent.engine.fix import verify_and_fix
from ai.dev_agent.engine.intent import wrote_files
from ai.dev_agent.engine.protocol import FINISH_NATIVE, FINISH_TEXT
from ai.dev_agent.engine.session import run_phase
from .support import AgentError, _Veto, _finished


class _WorkingMixin:
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
