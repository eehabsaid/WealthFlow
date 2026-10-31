"""Category 13: explain a calculation and its records. Proven by code: the total, the number of records and the largest amounts the answer
must name (and, as for every question, each figure must be in a tool result). The quality of the prose is not provable."""

from __future__ import annotations

from django.db.models import Count, Sum

from .. import phrasing
from ..fam_util import dec, expand, money, rows, unique_names


def _month_rows(qs, cid, y, m):
    return list(qs.filter(category_id=cid, date__year=y, date__month=m).order_by("-amount_base", "pk").values_list("amount_base", flat=True))


def _targets(user):
    qs, cats = rows(user, "Expense"), rows(user, "ExpenseCategory")
    if qs is None or cats is None:
        return []
    qs, out = qs.exclude(amount_base__isnull=True), []
    for cid, name in unique_names(cats).items():
        latest = qs.filter(category_id=cid).dates("date", "month")
        for d in list(latest)[-2:]:
            amounts = _month_rows(qs, cid, d.year, d.month)
            if len(amounts) >= 3 and dec(amounts[0]) > dec(amounts[1]) > 0:
                out.append((cid, name, d.year, d.month, amounts))
    return out


def train(user, langs, rng) -> list:
    out = []
    for cid, name, y, m, amounts in _targets(user):
        total = sum((dec(a) for a in amounts), dec(0))
        out += expand(f"explain_total:{cid}:{y}-{m:02d}", "explain_total", rng, langs,
                      [money(total), len(amounts), money(amounts[0]), money(amounts[1])],
                      lambda l, n=name, y=y, m=m: {"category": n, "month": phrasing.month(l, y, m)}, category="explain", level="complex")
    return out


def evaluate(user, langs, rng) -> list:
    out = []
    for cid, name, y, m, amounts in _targets(user)[:20]:
        total = sum((dec(a) for a in amounts), dec(0))
        out += expand(f"explain_largest:{cid}:{y}-{m:02d}", "explain_largest", rng, langs, [money(amounts[0]), money(total)],
                      lambda l, n=name, y=y, m=m: {"category": n, "month": phrasing.month(l, y, m)}, category="explain", level="complex", prefix="eval:")
    qs = rows(user, "Expense")
    if qs is not None:
        for r in list(qs.exclude(amount_base__isnull=True).values("date__year").annotate(t=Sum("amount_base"), c=Count("pk")).order_by("-date__year")[:2]):
            out += expand(f"explain_count:{r['date__year']}", "explain_count", rng, langs, [money(r["t"]), r["c"]],
                          lambda l, y=r["date__year"]: {"year": y}, category="explain", level="complex", prefix="eval:")
    return out
