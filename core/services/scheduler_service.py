from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, Optional, TypedDict

from core.services.certificate_automation_service import CertificateAutomationService
from core.services.certificate_interest_service import CertificateInterestService
from core.services.exchange_rate_service import ExchangeRateService
from core.services.gold_valuation_service import GoldValuationService
from core.services.property_valuation_service import PropertyValuationService
from core.services.reminder_automation_service import ReminderAutomationService


@dataclass
class ScheduledJobResult:
    job_id: str
    success: bool
    result: dict | None = None
    error: str | None = None

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
        }


class SchedulerJobSpec(TypedDict):
    label: str
    runner: Callable[[Optional[date]], dict]


class SchedulerService:
    def __init__(self):
        self._registry: dict[str, SchedulerJobSpec] = self._build_registry()

    def _build_registry(self) -> dict[str, SchedulerJobSpec]:
        return {
            "reminders": {
                "label": "Automatic reminders",
                "runner": lambda today=None: ReminderAutomationService().evaluate(today=today).to_dict(),
            },
            "certificate_maturity": {
                "label": "Certificate maturity",
                "runner": lambda today=None: CertificateAutomationService().close_matured_certificates(today=today).to_dict(),
            },
            "certificate_interest": {
                "label": "Certificate interest posting",
                "runner": lambda today=None: CertificateInterestService().synchronize(today=today).to_dict(),
            },
            "exchange_rates": {
                "label": "Exchange rates refresh",
                "runner": lambda today=None: ExchangeRateService().refresh_latest_rates().to_dict(),
            },
            "gold_prices": {
                "label": "Gold price refresh",
                "runner": lambda today=None: GoldValuationService().refresh_latest_prices().to_dict(),
            },
            "property_valuation": {
                "label": "Property valuation refresh",
                "runner": lambda today=None: PropertyValuationService().refresh_all(today=today).to_dict(),
            },
        }

    def list_jobs(self) -> list[dict[str, str]]:
        return [
            {"job_id": job_id, "label": spec["label"]}
            for job_id, spec in self._registry.items()
        ]

    def run_job(self, job_id: str, today: Optional[date] = None) -> dict[str, object]:
        spec = self._registry.get(job_id)
        if not spec:
            raise KeyError(job_id)
        return spec["runner"](today)

    def run_all(self, today: Optional[date] = None) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        for job_id in self._registry:
            try:
                result = self.run_job(job_id, today=today)
                results.append(ScheduledJobResult(job_id=job_id, success=True, result=result).to_dict())
            except Exception as exc:
                results.append(ScheduledJobResult(job_id=job_id, success=False, error=str(exc)).to_dict())
        return results
