"""TaskService: the one object every interface (web UI, VS Code extension, future ones) drives. It runs the SAME Agent as the command line, in a
background thread, one run at a time, and exposes start / approve / reject / stop / resume plus the live event log and pending approvals."""

from __future__ import annotations

import threading

from ai.dev_agent.engine import attachments as attachmentlib
from ai.dev_agent.engine import recovery
from ai.dev_agent.engine.cancel import CancelToken
from ai.dev_agent.engine.loop import Agent, AgentError
from ai.dev_agent.ledger.ledger import Ledger
from ai.dev_agent.memory.capture import capture
from ai.dev_agent.settings import store as settings_store
from ai.dev_agent.tools import proctree
from ai.dev_agent.service.approvals import QueueApprover
from ai.dev_agent.service.errors import Busy, ServiceError
from ai.dev_agent.service.events import EventLog
from ai.dev_agent.service.runstate import TASK_ID, Run


class TaskService:
    def __init__(self, project, provider_factory, settings_loader):
        self.project, self.provider_factory, self.settings_loader = project, provider_factory, settings_loader
        self._lock, self._run, self._logs = threading.RLock(), None, {}
        for task_id, reason in recovery.recover(project):   # tasks a crash left "running" become stopped, resumable tasks
            self.log(task_id).append({"type": "status", "status": "stopped", "reason": reason})

    # ---- state ----
    def log(self, task_id: str) -> EventLog:
        self.check_id(task_id)
        with self._lock:
            if task_id not in self._logs:
                self._logs[task_id] = EventLog(self.project.agent_dir / "tasks" / task_id / "events.jsonl")
            return self._logs[task_id]

    def state(self) -> dict:
        with self._lock:
            run = self._run
            return {"busy": run is not None, "current": {"id": run.task_id, "phase": run.phase} if run else None,
                    "approvals": run.approver.pending() if run else []}

    @staticmethod
    def check_id(task_id: str) -> str:
        if not isinstance(task_id, str) or not TASK_ID.match(task_id):
            raise ServiceError("invalid task id", "not_found")
        return task_id

    def ledger(self, task_id: str) -> Ledger:
        self.check_id(task_id)
        try:
            return Ledger.load(self.project, task_id)
        except FileNotFoundError as exc:
            raise ServiceError(str(exc), "not_found") from exc

    def list_tasks(self, limit: int = 50) -> list[dict]:
        rows = []
        for task_id in reversed(Ledger.list_ids(self.project)[-limit:]):
            try:
                d = Ledger.load(self.project, task_id).data
            except FileNotFoundError:
                continue
            rows.append({"id": task_id, "goal": d["goal"][:200], "status": d["status"], "updated": d["updated"], "stop_reason": d["stop_reason"][:200]})
        return rows

    # ---- actions ----
    def start_task(self, goal: str, attachments=None, override=None) -> str:
        """`override` ({provider, model}) applies to this task only (also when it is approved or resumed later); the shared settings are not touched."""
        goal = (goal or "").strip()
        if not goal or len(goal) > 8000:
            raise ServiceError("give a task of 1-8000 characters")
        override = self._override(override)
        settings, provider = self._provider(override)
        records = attachmentlib.prepare(self.project, attachments, settings, provider.has_vision())   # refuses with a clear message, never drops
        with self._lock:
            self._check_free()
            ledger = Ledger.create(self.project, goal)
            if override:
                ledger.data["model_override"] = override
            if records:
                meta = attachmentlib.save(ledger, records)
                self.log(ledger.id).append({"type": "attachments", "items": [{k: m[k] for k in ("name", "kind", "chars", "omitted")} for m in meta]})
            ledger.save()
            run = self._new_run(ledger.id)
            self._launch(run, lambda agent: agent.plan(goal, ledger), settings, provider)
        return ledger.id

    def approve_plan(self, task_id: str) -> None:
        settings, provider = self._provider(self.ledger(task_id).data.get("model_override"))
        with self._lock:
            self._check_free()
            if self.ledger(task_id).data["status"] != "awaiting_approval":
                raise ServiceError("this task has no plan waiting for approval", "conflict")
            self._launch(self._new_run(task_id), lambda agent: (agent.approve(task_id), agent.execute(task_id)), settings, provider)

    def resume(self, task_id: str) -> None:
        settings, provider = self._provider(self.ledger(task_id).data.get("model_override"))
        with self._lock:
            self._check_free()
            d = self.ledger(task_id).data
            if not d["plan"] or not d["approved_at"] or d["status"] not in ("stopped", "approved", "executing"):
                raise ServiceError("nothing to resume: start a new task", "conflict")
            self._launch(self._new_run(task_id), lambda agent: agent.execute(task_id), settings, provider)

    def reject_plan(self, task_id: str) -> None:
        with self._lock:
            self._check_free()
            ledger = self.ledger(task_id)
            if ledger.data["status"] != "awaiting_approval":
                raise ServiceError("this task has no plan waiting for approval", "conflict")
            ledger.set_status("rejected", "plan rejected by the owner")
            capture(ledger)
            self.log(task_id).append({"type": "status", "status": "rejected", "reason": "plan rejected by the owner"})

    def stop(self) -> bool:
        with self._lock:
            run = self._run
        if run:
            run.cancel.set("stopped by user")
        return bool(run)

    def answer_approval(self, approval_id: str, approve: bool) -> bool:
        with self._lock:
            run = self._run
        return bool(run) and run.approver.answer(approval_id, approve)

    def shutdown(self, wait: float = 15.0) -> None:
        self.stop()
        with self._lock:
            thread = self._run.thread if self._run else None
        if thread:
            thread.join(wait)
        proctree.kill_all()
        for log in list(self._logs.values()):
            log.close()

    # ---- internals ----
    @staticmethod
    def _override(override) -> dict | None:
        if not override:
            return None
        if not isinstance(override, dict) or not all(isinstance(override.get(k, ""), str) for k in ("provider", "model")):
            raise ServiceError("the model choice must be {provider, model} as text")
        return {k: override[k].strip() for k in ("provider", "model") if override.get(k, "").strip()} or None

    def _provider(self, override: dict | None = None):
        settings = self.settings_loader()
        if override:
            settings = {**settings, **override}
            settings_store.validate(settings)   # unknown provider / credential-looking value -> SettingsError (HTTP 400)
        return settings, self.provider_factory(settings)

    def _check_free(self) -> None:
        if self._run is not None:
            raise Busy()

    def _new_run(self, task_id: str) -> Run:
        cancel, log = CancelToken(), self.log(task_id)
        run = Run(task_id, cancel, QueueApprover(lambda e: self._emit(run, log, e), cancel))
        return run

    def _emit(self, run: Run, log: EventLog, event: dict) -> None:
        if event.get("type") == "phase":
            run.phase = event["phase"]
        elif event.get("type") == "package" and event.get("status") == "running":
            run.phase = f"executing {event['id']}"
        log.append(event)

    def _launch(self, run: Run, job, settings: dict, provider) -> None:
        log = self.log(run.task_id)
        agent = Agent(self.project, provider, settings, run.approver, lambda e: self._emit(run, log, e), run.cancel)

        def work():
            status = "stopped"
            try:
                job(agent)
            except (AgentError, ServiceError) as exc:
                log.append({"type": "error", "message": str(exc)})
            except Exception as exc:   # an engine bug must end the run visibly, never leave the task hanging
                log.append({"type": "error", "message": f"internal error: {type(exc).__name__}: {exc}"})
                try:
                    self.ledger(run.task_id).set_status("stopped", f"internal error: {type(exc).__name__}: {exc}")
                except ServiceError:
                    pass
            finally:
                try:
                    status = self.ledger(run.task_id).data["status"]
                except ServiceError:
                    pass
                log.append({"type": "done", "status": status})
                with self._lock:
                    self._run = None

        run.thread = threading.Thread(target=work, name=f"task-{run.task_id}", daemon=True)
        self._run = run
        run.thread.start()
