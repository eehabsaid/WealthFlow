"""Bank balances, posted interest and active certificate principal from owner-scoped records."""

from __future__ import annotations

from collections import defaultdict

from django.db.models import Q, Sum

from core.models import _is_certificate_active

from ..fam_util import dec, expand, money, nonzero, rows, unique_names


def _banks(user) -> dict:
    qs = rows(user, "Bank")
    return unique_names(qs) if qs is not None else {}


def train(user, langs, rng) -> list:
    out, banks = [], _banks(user)

    balances = rows(user, "BalanceEntry")
    if balances is not None and banks:
        groups = balances.filter(
            Q(balance_type__iexact="cash") | Q(balance_type__iexact="bank"),
            bank_id__in=banks,
            currency__code__isnull=False,
            currency__owner=user,
        ).values("bank_id", "currency_id", "currency__code").annotate(total=Sum("amount"))
        for r in groups:
            total = dec(r["total"])
            if nonzero([total]):
                bid, currency = r["bank_id"], r["currency__code"]
                out += expand(
                    f"bank_balance:{bid}:{r['currency_id']}", "bank_balance", rng, langs, [money(total)],
                    lambda l, b=banks[bid], c=currency: {"bank": b, "currency": c},
                    category="banking", level="intermediate",
                )

    interest = rows(user, "BankInterest")
    if interest is not None and banks:
        groups = interest.filter(bank_id__in=banks, bank__owner=user, currency__owner=user, currency__code__isnull=False).values(
            "bank_id", "currency_id", "currency__code", "interest_date__year"
        ).annotate(total=Sum("amount"))
        for r in groups:
            total = dec(r["total"])
            if nonzero([total]):
                bid, year, currency = r["bank_id"], r["interest_date__year"], r["currency__code"]
                out += expand(
                    f"bank_interest_year:{bid}:{year}:{r['currency_id']}", "bank_interest_year", rng, langs,
                    [money(total)], lambda l, b=banks[bid], y=year, c=currency: {"bank": b, "year": y, "currency": c},
                    category="banking", level="intermediate",
                )

    history = rows(user, "BankCertificateInterestHistory")
    if history is not None:
        groups = history.filter(currency__owner=user, currency__code__isnull=False).values(
            "currency_id", "currency__code", "posting_date__year"
        ).annotate(total=Sum("interest_amount"))
        for r in groups:
            total = dec(r["total"])
            if nonzero([total]):
                year, currency = r["posting_date__year"], r["currency__code"]
                out += expand(
                    f"certificate_interest_year:{year}:{r['currency_id']}", "certificate_interest_year", rng, langs,
                    [money(total)], lambda l, y=year, c=currency: {"year": y, "currency": c},
                    category="banking", level="intermediate",
                )
    return out


def evaluate(user, langs, rng) -> list:
    certificates, banks = rows(user, "BankCertificate"), _banks(user)
    if certificates is None or not banks:
        return []

    totals = defaultdict(lambda: dec(0))
    for certificate in certificates.select_related("bank", "currency").filter(bank__owner=user, currency__owner=user):
        if certificate.bank_id not in banks or not certificate.currency_id or not _is_certificate_active(certificate):
            continue
        totals[(certificate.bank_id, certificate.currency_id, certificate.currency.code)] += dec(certificate.amount)

    out = []
    for (bank_id, currency_id, currency), total in totals.items():
        if nonzero([total]):
            out += expand(
                f"certificate_principal:{bank_id}:{currency_id}", "certificate_principal", rng, langs,
                [money(total)], lambda l, b=banks[bank_id], c=currency: {"bank": b, "currency": c},
                category="banking", level="intermediate", prefix="eval:",
            )
    return out
