"""Income record extraction for Income Analytics (read-only).

One normalized row per source record, every amount in the owner's base currency.
Sources: salary, bonus, perdiem, cert (real interest postings only), bank, rent, manual, sale.
"""
from decimal import Decimal

from core.models import (
    AssetSale,
    BankCertificateInterestHistory,
    BankInterest,
    MonthlyIncomeAdjustment,
    PerDiem,
    RentReceipt,
    SalaryEntry,
)
from core.services.reports.income_summary_service import MONTH_NAMES
from core.services.shared.base_currency import get_user_base_code
from core.services.shared.currency_conversion_service import CurrencyConversionService

SOURCES = [
    {"id": "salary", "color": "#1a6ef5"},
    {"id": "bonus", "color": "#00d68f"},
    {"id": "perdiem", "color": "#a78bfa"},
    {"id": "cert", "color": "#ffd166"},
    {"id": "bank", "color": "#00b4d8"},
    {"id": "rent", "color": "#ff8fab"},
    {"id": "manual", "color": "#94a3b8"},
    {"id": "sale", "color": "#f97316"},
]
SOURCE_IDS = [s["id"] for s in SOURCES]

MONTH_NUM = {name: i + 1 for i, name in enumerate(MONTH_NAMES)}
TWO_PLACES = Decimal("0.01")


def _convert(amount, code, base_code, rates):
    amt = Decimal(str(amount or 0))
    if not code:
        return float(amt.quantize(TWO_PLACES))
    rate = rates.get(code)
    if rate is None:
        rate = CurrencyConversionService.calculate_exchange_rate(code, base_code)
    return float((amt * rate).quantize(TWO_PLACES))


def _salary_rows(owner, basis):
    rows = []
    for e in SalaryEntry.objects.filter(company__owner=owner).select_related("company"):
        month = MONTH_NUM.get(str(e.month).strip().lower())
        if month is None:
            continue
        salary_amt = e.paid
        if basis == "gross" and e.gross is not None:
            salary_amt = e.gross
        ref = e.company.display_name or e.company.name
        rows.append({
            "source": "salary", "year": e.year, "month": month, "ref": ref,
            "amount": float(salary_amt), "date": f"{e.year}-{month:02d}",
        })
        if e.bonus and float(e.bonus) > 0:
            rows.append({
                "source": "bonus", "year": e.year, "month": month, "ref": ref,
                "amount": float(e.bonus), "date": f"{e.year}-{month:02d}",
            })
    return rows


def _perdiem_rows(owner):
    rows = []
    for e in PerDiem.objects.filter(company__owner=owner):
        rows.append({
            "source": "perdiem", "year": e.date.year, "month": e.date.month,
            "ref": f"#{e.id}", "amount": float(e.amount_base), "date": e.date.isoformat(),
        })
    return rows


def _cert_rows(owner):
    """Real BankCertificateInterestHistory postings only (no active-certificate projection)."""
    rows = []
    for h in BankCertificateInterestHistory.objects.filter(
        certificate__owner=owner
    ).order_by("posting_date", "id"):
        rows.append({
            "source": "cert", "year": h.posting_date.year, "month": h.posting_date.month,
            "ref": f"#{h.certificate_id}", "amount": float(h.interest_amount),
            "date": h.posting_date.isoformat(),
        })
    return rows


def _bank_rows(owner, base_code, rates):
    rows = []
    for e in BankInterest.objects.filter(owner=owner).select_related("bank", "currency"):
        rows.append({
            "source": "bank", "year": e.interest_date.year, "month": e.interest_date.month,
            "ref": e.bank.name if e.bank else f"#{e.id}",
            "amount": _convert(e.amount, e.currency.code if e.currency else "", base_code, rates),
            "date": e.interest_date.isoformat(),
        })
    return rows


def _rent_rows(owner, base_code, rates):
    rows = []
    for e in RentReceipt.objects.filter(owner=owner).select_related(
        "rental__asset", "currency"
    ):
        asset = e.rental.asset if e.rental else None
        rows.append({
            "source": "rent", "year": e.period_start.year, "month": e.period_start.month,
            "ref": asset.name if asset else f"#{e.id}",
            "amount": _convert(e.amount, e.currency.code if e.currency else "", base_code, rates),
            "date": e.period_start.isoformat(),
        })
    return rows


def _manual_rows(owner):
    rows = []
    for e in MonthlyIncomeAdjustment.objects.filter(owner=owner).order_by("year", "month"):
        rows.append({
            "source": "manual", "year": e.year, "month": e.month,
            "ref": f"#{e.id}", "amount": float(e.amount), "date": f"{e.year}-{e.month:02d}",
        })
    return rows


def _sale_rows(owner, base_code, rates):
    rows = []
    for e in AssetSale.objects.filter(asset__owner=owner).select_related(
        "asset", "deposit_currency"
    ):
        rows.append({
            "source": "sale", "year": e.sale_date.year, "month": e.sale_date.month,
            "ref": e.asset.name if e.asset else f"#{e.id}",
            "amount": _convert(
                e.net_sale_amount,
                e.deposit_currency.code if e.deposit_currency else "",
                base_code, rates,
            ),
            "date": e.sale_date.isoformat(),
        })
    return rows


def extract_all(owner, basis="net"):
    """Every income record of the owner, normalized, in the base currency."""
    base_code = get_user_base_code(owner)
    rates = CurrencyConversionService.get_rates_to_base(base_code)
    rows = []
    rows += _salary_rows(owner, basis)
    rows += _perdiem_rows(owner)
    rows += _cert_rows(owner)
    rows += _bank_rows(owner, base_code, rates)
    rows += _rent_rows(owner, base_code, rates)
    rows += _manual_rows(owner)
    rows += _sale_rows(owner, base_code, rates)
    return rows
