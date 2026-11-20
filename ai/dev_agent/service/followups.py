"""Starting tasks: a new chat, or a follow-up in an open chat. A follow-up sent while a task is running waits in `_queue` (status "queued") and starts, in the
order it was sent, when that run ends. Mixed into TaskService (service/tasks.py), which owns the run, the lock and the logs used here."""

from __future__ import annotations

from ai.dev_agent.engine import attachments as attachmentlib
from ai.dev_agent.engine import chat as chatlib
from ai.dev_agent.ledger.ledger import Ledger
from ai.dev_agent.service.errors import Busy, ServiceError


class FollowUps:
    def start_task(self, goal: str, attachments=None, override=None, chat: str = "") -> str:
        """`override` ({provider, model}) applies to this task only (also when it is approved or resumed later); the shared settings are not touched.
        `chat` = id of any task of the chat this message continues: the new task joins that chat and starts with what the earlier tasks did.
        A follow-up sent while another task is running waits in the queue (status "queued") and starts when that task ends; a new chat is refused (Busy)."""
        goal = (goal or "").strip()
        if not goal or len(goal) > 8000:
            raise ServiceError("give a task of 1-8000 characters")
        override = self._override(override)
        settings, provider = self._provider(override)
        records = attachmentlib.prepare(self.project, attachments, settings, provider.has_vision())   # refuses with a clear message, never drops
        with self._lock:
            chat_id = chatlib.chat_of(self.ledger(chat).data) if chat else ""
            queued = self._run is not None and bool(chat_id)
            if self._run is not None and not queued:
                raise Busy()
            ledger = Ledger.create(self.project, goal, chat_id, status="queued" if queued else "planning")
            if chat_id:
                ledger.data["chat_context"] = chatlib.context(self.project, chat_id, before=ledger.data)
            if override:
                ledger.data["model_override"] = override
            if records:
                meta = attachmentlib.save(ledger, records)
                self.log(ledger.id).append({"type": "attachments", "items": [{k: m[k] for k in ("name", "kind", "chars", "omitted")} for m in meta]})
            ledger.save()
            if queued:
                self._queue.append(ledger.id)
                self.log(ledger.id).append({"type": "status", "status": "queued", "reason": "waits for the running task to finish"})
            else:
                self._launch(self._new_run(ledger.id), self._plan_job(ledger), settings, provider)
        return ledger.id

    @staticmethod
    def _plan_job(ledger):
        """Plan approval on: plan, then wait for the owner. Plan approval off (Settings > Behavior): no planning phase, the work starts at once."""
        return lambda agent: agent.start(ledger.data["goal"], ledger)

    def _start_queued(self) -> None:
        """Called (lock held) when a run ends: start the oldest waiting follow-up. A follow-up that cannot start is stopped with the reason."""
        while self._queue and self._run is None:
            task_id = self._queue.pop(0)
            try:
                ledger = self.ledger(task_id)
                if ledger.data["status"] != "queued":
                    continue   # stopped or removed while waiting
                settings, provider = self._provider(ledger.data.get("model_override"))
                ledger.data["status"] = "planning"
                ledger.save()
                self.log(task_id).append({"type": "status", "status": "planning", "reason": ""})
                self._launch(self._new_run(task_id), self._plan_job(ledger), settings, provider)
            except Exception as exc:   # e.g. the model settings changed and are now invalid: say so on that task, then try the next one
                try:
                    self.ledger(task_id).set_status("stopped", f"could not start the queued follow-up: {exc}")
                    self.log(task_id).append({"type": "status", "status": "stopped", "reason": f"could not start the queued follow-up: {exc}"})
                    self.log(task_id).append({"type": "done", "status": "stopped"})
                except ServiceError:
                    pass

    def _clear_queue(self, reason: str) -> None:
        for task_id in self._queue:
            try:
                self.ledger(task_id).set_status("stopped", reason)
                self.log(task_id).append({"type": "status", "status": "stopped", "reason": reason})
                self.log(task_id).append({"type": "done", "status": "stopped"})
            except ServiceError:
                pass
        self._queue = []
