"""
Certificate eligibility and due-date calculation helpers.

Split out of the former monolithic certificate_interest_service.py
(200-line rule). These never touch timezone.localdate() or transaction
handling, so they're safe to move out of __init__.py.
"""

import calendar
from datetime import date

from django.db.models import Max

from core.models import BalanceEntry, BankCertificateInterestHistory


class DateCalculationMixin:
    def _is_eligible(self, certificate, today):
        if not certificate:
            return False
        status = str(certificate.status or "").strip().lower()
        if status != "active":
            return False
        if not certificate.issue_date or not certificate.expiry_date:
            return False
        if today < certificate.issue_date:
            return False
        if today > certificate.expiry_date:
            return False
        return True

    def _frequency_interval_months(self, frequency_value):
        normalized = str(frequency_value or "").strip().lower()
        return self.FREQUENCY_MONTHS.get(normalized)

    def _get_due_dates(self, certificate, today, history_last=None):
        interval_months = self.FREQUENCY_MONTHS.get(
            str(certificate.frequency or "").strip().lower()
        )
        if not interval_months:
            return []

        last_posted = self._effective_last_posted_date(certificate, today, history_last=history_last)
        due_dates = []
        period_index = 1

        while True:
            due_date = self._scheduled_due_date(
                certificate.issue_date, interval_months, period_index
            )

            if due_date > today or due_date > certificate.expiry_date:
                break

            if last_posted is None or due_date > last_posted:
                due_dates.append(due_date)

            period_index += 1

        return due_dates

    def _effective_last_posted_date(self, certificate, today, history_last=None):
        if history_last is None:
            history_last = (
                BankCertificateInterestHistory.objects.filter(
                    certificate=certificate,
                    posting_date__lte=today,
                ).aggregate(last=Max("posting_date"))
                .get("last")
            )

        if certificate.last_interest_posted_date and history_last:
            return max(certificate.last_interest_posted_date, history_last)
        return certificate.last_interest_posted_date or history_last

    def _scheduled_due_date(self, issue_date, interval_months, period_index):
        return self._add_months(issue_date, interval_months * period_index)

    def _get_target_balance_entry(self, certificate):
        return (
            BalanceEntry.objects.select_for_update()
            .filter(
                balance_type=BalanceEntry.BalanceType.CASH,
                bank_id=certificate.bank_id,
                currency_id=certificate.currency_id,
            )
            .order_by("id")
            .first()
        )

    def _build_posting_period_label(self, certificate, due_date):
        frequency = str(certificate.frequency or "").strip() or "Period"
        return f"{frequency}:{due_date.isoformat()}"

    def _add_months(self, base_date, months):
        month_index = base_date.month - 1 + months
        year = base_date.year + month_index // 12
        month = month_index % 12 + 1
        day = min(base_date.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
