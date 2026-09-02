from __future__ import annotations

from core.constants import MONTH_ORDER
from core.models import Company, ReminderLog, SalaryEntry


class SalaryCustomMixin:
    """Evaluates salary-unpaid, salary-day, and custom reminder rules."""

    def _evaluate_salary_unpaid(self, rule, today):
        trigger_day = self._salary_trigger_day(rule, today)
        if today.day < trigger_day:
            return []

        # month is stored as a full English name (e.g. "July"), derive it from MONTH_ORDER
        month_name = MONTH_ORDER[today.month - 1]

        # Fire if ANY active company has no salary record for this month,
        # or has a record but paid == 0 (nothing paid yet).
        should_fire = False
        for company in Company.objects.filter(is_active=True):
            try:
                entry = SalaryEntry.objects.get(
                    company=company,
                    year=today.year,
                    month__iexact=month_name,
                )
                # Record exists — fire only if nothing has been paid yet
                if float(entry.paid) == 0:
                    should_fire = True
                    break
            except SalaryEntry.DoesNotExist:
                # No record at all for this company this month — treat as unpaid
                should_fire = True
                break

        if not should_fire:
            return []

        message = rule.salary_message or "This month has unpaid salary entries."
        ReminderLog.objects.get_or_create(
            rule=rule,
            related_model="SalaryEntry",
            related_id=0,
            fired_on=today,
            defaults={"message": message},
        )
        return [
            {
                "rule_id": rule.id,
                "rule_name": rule.name,
                "rule_type": rule.rule_type,
                "message": message,
                "link": "salary",
            }
        ]

    def _evaluate_salary_day(self, rule, today):
        trigger_day = self._salary_trigger_day(rule, today)
        if today.day < trigger_day:
            return []

        message = rule.salary_message or f'Salary day reminder for {today.strftime("%B %Y")}. '
        ReminderLog.objects.get_or_create(
            rule=rule,
            related_model="SalaryDay",
            related_id=today.month,
            fired_on=today,
            defaults={"message": message},
        )
        return [
            {
                "rule_id": rule.id,
                "rule_name": rule.name,
                "rule_type": rule.rule_type,
                "message": message,
                "link": "salary",
            }
        ]

    def _evaluate_custom(self, rule, today):
        trigger_day = self._salary_trigger_day(rule, today)
        if today.day < trigger_day:
            return []

        message = rule.salary_message or rule.name
        ReminderLog.objects.get_or_create(
            rule=rule,
            related_model="Custom",
            related_id=today.month,
            fired_on=today,
            defaults={"message": message},
        )
        return [
            {
                "rule_id": rule.id,
                "rule_name": rule.name,
                "rule_type": rule.rule_type,
                "message": message,
                "link": "",
            }
        ]

    def _salary_trigger_day(self, rule, today):
        import calendar as cal

        last_day = cal.monthrange(today.year, today.month)[1]
        trigger = str(rule.salary_trigger or "").strip().lower()
        if trigger == "day_of_month":
            return min(int(rule.salary_day or 1), last_day)
        if trigger == "days_before_eom":
            return max(1, last_day - int(rule.salary_day or 1))
        if trigger == "days_after_som":
            return min(int(rule.salary_day or 1) + 1, last_day)
        return min(int(rule.salary_day or 1), last_day)

    def _clamp_int(self, raw_value, default, min_value, max_value):
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            value = default
        return max(min_value, min(max_value, value))
