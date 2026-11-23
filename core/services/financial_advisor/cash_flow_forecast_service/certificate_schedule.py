"""
Certificate interest / maturity schedule — the single derivation used by BOTH
CashFlowForecastService and the Commitments Calendar, so the two can never
disagree.

Rules (unchanged from the forecast):
- only active certificates with issue + expiry dates that have not expired;
- interest dates come from CertificateInterestService (issue date + N months);
- an interest date that is not after today, or not after the last posted
  interest (certificate field or interest history), is already paid and skipped;
- the interest due ON the expiry date is folded into the maturity amount, so
  it is neither double counted nor lost;
- a certificate whose per-period interest converts to <= 0 base is skipped.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, List

from django.db.models import Max

from core.models import BankCertificate, BankCertificateInterestHistory, _is_certificate_active


def _to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class CertificateScheduleItem:
    event_date: date
    event_type: str  # "certificate_interest" | "certificate_maturity"
    certificate: BankCertificate
    currency_code: str
    amount: float  # certificate's own currency (maturity = principal + folded interest)
    amount_base: float  # converted exactly the way the forecast converts
    principal: float = 0.0  # maturity only, own currency
    interest: float = 0.0  # maturity only: interest folded into maturity, own currency


def build_certificate_schedule(
    owner,
    today: date,
    until: date,
    interest_service,
    convert: Callable[[float, str], float],
) -> List[CertificateScheduleItem]:
    certs = [c for c in BankCertificate.objects.select_related("bank", "currency").filter(owner=owner)
             if _is_certificate_active(c)]
    if not certs:
        return []

    history_rows = (
        BankCertificateInterestHistory.objects
        .filter(certificate_id__in=[c.id for c in certs], posting_date__lte=today)
        .values("certificate_id")
        .annotate(last_posting=Max("posting_date"))
    )
    history_map = {row["certificate_id"]: row["last_posting"] for row in history_rows}

    items: List[CertificateScheduleItem] = []
    for cert in certs:
        if not cert.issue_date or not cert.expiry_date or cert.expiry_date <= today:
            continue

        interval = interest_service._frequency_interval_months(cert.frequency)
        code = str(getattr(cert.currency, "code", "") or "").upper()
        principal = _to_float(cert.amount)
        interest = _to_float(cert.interest_value)
        interest_base = convert(interest, code)
        if interest_base <= 0:
            continue

        maturity_interest = 0.0
        maturity_interest_base = 0.0
        if interval:
            last_posted = cert.last_interest_posted_date
            history_last = history_map.get(cert.id)
            effective_last = max(last_posted, history_last) if last_posted and history_last else last_posted or history_last

            index = 1
            due = interest_service._scheduled_due_date(cert.issue_date, interval, index)
            while due <= cert.expiry_date and due <= until:
                if due > today and (effective_last is None or due > effective_last):
                    if due < cert.expiry_date:
                        items.append(CertificateScheduleItem(due, "certificate_interest", cert, code, interest, interest_base))
                    else:
                        maturity_interest += interest
                        maturity_interest_base += interest_base
                index += 1
                due = interest_service._scheduled_due_date(cert.issue_date, interval, index)

        if cert.expiry_date <= until:
            items.append(CertificateScheduleItem(
                cert.expiry_date, "certificate_maturity", cert, code,
                principal + maturity_interest, convert(principal, code) + maturity_interest_base,
                principal=principal, interest=maturity_interest,
            ))
    return items
