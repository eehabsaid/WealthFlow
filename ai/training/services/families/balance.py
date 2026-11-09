"""Relational balance movements, keeping amounts in their recorded currencies."""

from __future__ import annotations

from django.db.models import Sum

from ai.training.services.fam_util import dec, expand, money, nonzero, rows


def train(user, langs, rng) -> list:
    transfers = rows(user, "BalanceTransfer")
    if transfers is None:
        return []

    groups = transfers.filter(currency__owner=user).values("transfer_date__year", "currency_id", "currency__code").annotate(
        amount=Sum("amount"), fees=Sum("fee")
    )
    out = []
    for r in groups:
        amount, fees = dec(r["amount"]), dec(r["fees"])
        if nonzero([amount, fees]) and r["currency__code"]:
            year, currency_id, currency = r["transfer_date__year"], r["currency_id"], r["currency__code"]
            out += expand(
                f"transfer_year:{year}:{currency_id}", "transfer_year", rng, langs, [money(amount), money(fees)],
                lambda l, y=year, c=currency: {"year": y, "currency": c},
                category="balance", level="intermediate",
            )
    return out


def evaluate(user, langs, rng) -> list:
    exchanges = rows(user, "CurrencyExchange")
    if exchanges is None:
        return []

    groups = exchanges.filter(
        from_balance__owner=user,
        to_balance__owner=user,
        from_currency__owner=user,
        to_currency__owner=user,
        reversed_at__isnull=True,
    ).values(
        "exchange_date__year", "from_currency_id", "from_currency__code", "to_currency_id", "to_currency__code"
    ).annotate(from_total=Sum("from_amount"), to_total=Sum("to_amount"))
    out = []
    for r in groups:
        from_total, to_total = dec(r["from_total"]), dec(r["to_total"])
        if nonzero([from_total, to_total]) and r["from_currency__code"] and r["to_currency__code"]:
            year = r["exchange_date__year"]
            from_code, to_code = r["from_currency__code"], r["to_currency__code"]
            out += expand(
                f"exchange_year:{year}:{r['from_currency_id']}:{r['to_currency_id']}", "exchange_year", rng, langs,
                [money(from_total), money(to_total)],
                lambda l, y=year, f=from_code, t=to_code: {"year": y, "from_currency": f, "to_currency": t},
                category="balance", level="complex", prefix="eval:",
            )
    return out
