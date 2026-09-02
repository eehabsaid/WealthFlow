"""
core/services/shared/reminder_automation_service package.

Sibling modules:
- certificate_insurance_mixin.py  — CertificateInsuranceMixin: cert-maturity & insurance-expiry rules
- vehicle_property_mixin.py       — VehiclePropertyMixin: vehicle-license & property-tax rules
- salary_custom_mixin.py          — SalaryCustomMixin: salary-unpaid, salary-day, custom rules,
                                      plus the shared _salary_trigger_day / _clamp_int helpers

This file re-exports ReminderAutomationResult and ReminderAutomationService, the public entry points.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from core.models import ReminderRule

from core.services.shared.reminder_automation_service.certificate_insurance_mixin import (
    CertificateInsuranceMixin,
)
from core.services.shared.reminder_automation_service.vehicle_property_mixin import (
    VehiclePropertyMixin,
)
from core.services.shared.reminder_automation_service.salary_custom_mixin import (
    SalaryCustomMixin,
)


@dataclass
class ReminderAutomationResult:
    reminders: list

    @property
    def count(self) -> int:
        return len(self.reminders)

    def to_dict(self):
        return {"reminders": self.reminders, "count": self.count}


class ReminderAutomationService(CertificateInsuranceMixin, VehiclePropertyMixin, SalaryCustomMixin):
    """Evaluates active reminder rules and event-based reminders in one place."""

    def evaluate(self, today=None):
        current_date = today or timezone.localdate()
        reminders = []

        with transaction.atomic():
            for rule in ReminderRule.objects.filter(is_active=True):
                reminders.extend(self._evaluate_rule(rule, current_date))

        return ReminderAutomationResult(reminders=reminders)

    def _evaluate_rule(self, rule, today):
        rule_type = str(rule.rule_type or "").strip().lower()
        if rule_type == "cert_maturity":
            return self._evaluate_certificate_maturity(rule, today)
        if rule_type == "insurance_expiry":
            return self._evaluate_insurance_expiry(rule, today)
        if rule_type == "vehicle_license_expiry":
            return self._evaluate_vehicle_license_expiry(rule, today)
        if rule_type == "property_tax_reminder":
            return self._evaluate_property_tax_reminder(rule, today)
        if rule_type == "salary_unpaid":
            return self._evaluate_salary_unpaid(rule, today)
        if rule_type == "salary_day":
            return self._evaluate_salary_day(rule, today)
        if rule_type == "custom":
            return self._evaluate_custom(rule, today)
        return []


__all__ = ["ReminderAutomationResult", "ReminderAutomationService"]
