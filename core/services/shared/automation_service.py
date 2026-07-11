from __future__ import annotations

from datetime import date

from core.services.shared.scheduler_service import SchedulerService

class AutomationService:
    """Central automation orchestrator used by the scheduler command."""

    def __init__(self):
        self.scheduler = SchedulerService()

    def run_all(self, today: date | None = None) -> list[dict[str, object]]:
        return self.scheduler.run_all(today=today)
