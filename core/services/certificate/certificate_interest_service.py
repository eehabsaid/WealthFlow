import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from core.models import BalanceEntry, BankCertificate, BankCertificateInterestHistory

@dataclass
class CertificateInterestSyncResult:
    processed_certificates: int = 0
    posted_periods: int = 0
    total_interest_posted: Decimal = Decimal("0")

    def to_dict(self):
        return {
            "processed_certificates": self.processed_certificates,
            "posted_periods": self.posted_periods,
            "total_interest_posted": float(self.total_interest_posted or 0),
        }

class CertificateInterestService:
    FREQUENCY_MONTHS = {
        "monthly": 1,
        "quarterly": 3,
        "semi-yearly": 6,
        "semi yearly": 6,
        "semiannual": 6,
        "semi-annual": 6,
        "semi annually": 6,
        "semi-annually": 6,
        "yearly": 12,
        "annual": 12,
        "annually": 12,
    }

    def synchronize(self, today=None):
        current_date = today or timezone.localdate()
        result = CertificateInterestSyncResult()

        with transaction.atomic():
            certificates = list(
                BankCertificate.objects.select_related("bank", "currency")
                .select_for_update()
                .all()
            )

            # Pre-load target cash balance entries in 1 query
            cash_entries = list(
                BalanceEntry.objects.select_for_update()
                .filter(balance_type=BalanceEntry.BalanceType.CASH)
                .order_by("id")
            )
            target_entry_map = {}
            for entry in cash_entries:
                key = (entry.bank_id, entry.currency_id)
                if key not in target_entry_map:
                    target_entry_map[key] = entry

            # Pre-load max posting date per certificate in 1 query
            history_lasts = dict(
                BankCertificateInterestHistory.objects.filter(posting_date__lte=current_date)
                .values("certificate_id")
                .annotate(last=Max("posting_date"))
                .values_list("certificate_id", "last")
            )

            for certificate in certificates:
                if not self._is_eligible(certificate, current_date):
                    continue

                history_last = history_lasts.get(certificate.id)
                due_dates = self._get_due_dates(certificate, current_date, history_last=history_last)
                if not due_dates:
                    continue

                target_entry = target_entry_map.get((certificate.bank_id, certificate.currency_id))
                if not target_entry:
                    target_entry = self._get_target_balance_entry(certificate)
                if not target_entry:
                    raise ValueError("matching_balance_entry_not_found")

                posted_count = 0
                latest_processed_date = certificate.last_interest_posted_date
                interest_amount = Decimal(certificate.interest_value or 0)

                for due_date in due_dates:
                    _, created = BankCertificateInterestHistory.objects.get_or_create(
                        certificate=certificate,
                        posting_date=due_date,
                        defaults={
                            "posting_period": self._build_posting_period_label(certificate, due_date),
                            "interest_amount": interest_amount,
                            "bank_id": certificate.bank_id,
                            "currency_id": certificate.currency_id,
                        },
                    )
                    if created:
                        posted_count += 1
                    if latest_processed_date is None or due_date > latest_processed_date:
                        latest_processed_date = due_date

                if latest_processed_date != certificate.last_interest_posted_date:
                    certificate.last_interest_posted_date = latest_processed_date
                    certificate.save(update_fields=["last_interest_posted_date", "updated_at"])

                if posted_count <= 0:
                    continue

                target_entry.amount = Decimal(target_entry.amount or 0) + (interest_amount * posted_count)
                target_entry.save(update_fields=["amount"])

                result.processed_certificates += 1
                result.posted_periods += posted_count
                result.total_interest_posted += interest_amount * posted_count

        return result

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
