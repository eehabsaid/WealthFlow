"""Categories 4 and 9: expense categories, subcategories, month/year comparisons and shares. Figures: Expense.amount_base (base currency)
summed by Django on the owner's rows. Ties at the top and all-zero answers are skipped."""

from __future__ import annotations

from collections import defaultdict
from django.db.models import Count, Sum

from .. import phrasing
from ..fam_util import dec, expand, money, nonzero, percent, rows, unique_names


def _expenses(user):
    qs = rows(user, "Expense")
    return qs.exclude(amount_base__isnull=True) if qs is not None else None


def _month_totals(qs) -> dict:
    return {(r["date__year"], r["date__month"]): dec(r["t"]) for r in qs.values("date__year", "date__month").annotate(t=Sum("amount_base"))}


def _pairs(totals: dict, limit: int = 4) -> list:
    keys = sorted(totals)
    return [(a, b) for a, b in zip(keys, keys[1:]) if (b[0] * 12 + b[1]) - (a[0] * 12 + a[1]) == 1][-limit:]


def _categories(user) -> dict:
    cats = rows(user, "ExpenseCategory")
    return unique_names(cats) if cats is not None else {}


def train(user, langs, rng) -> list:
    qs, out = _expenses(user), []
    if qs is None or not qs.exists():
        return out
    for cid, name in _categories(user).items():
        mine = qs.filter(category_id=cid)
        by_month, by_year = _month_totals(mine), defaultdict(lambda: dec(0))
        for (y, _), t in by_month.items():
            by_year[y] += t
        for (y, m) in sorted(by_month)[-2:]:
            if nonzero([by_month[(y, m)]]):
                out += expand(f"cat_month:{cid}:{y}-{m:02d}", "cat_month", rng, langs, [money(by_month[(y, m)])],
                              lambda l, n=name, y=y, m=m: {"category": n, "month": phrasing.month(l, y, m)}, category="expenses")
        for y in sorted(by_year)[-1:]:
            if nonzero([by_year[y]]):
                out += expand(f"cat_year:{cid}:{y}", "cat_year", rng, langs, [money(by_year[y])], lambda l, n=name, y=y: {"category": n, "year": y}, category="expenses")
    for y in sorted({d.year for d in qs.dates("date", "year")})[-3:]:
        tops = list(qs.filter(date__year=y, category__isnull=False).values("category_id", "category__name").annotate(t=Sum("amount_base")).order_by("-t")[:2])
        if len(tops) == 2 and tops[0]["t"] != tops[1]["t"] and tops[0]["category__name"]:
            out += expand(f"top_category:{y}", "top_category", rng, langs, [money(tops[0]["t"])],
                          lambda l, y=y: {"year": y}, category="expenses", level="complex")
    totals = _month_totals(qs)
    for a, b in _pairs(totals):
        if nonzero([totals[a], totals[b]]) and totals[a] != totals[b]:
            out += expand(f"month_change:{a[0]}-{a[1]:02d}:{b[0]}-{b[1]:02d}", "month_change", rng, langs,
                          [money(totals[a]), money(totals[b]), money(totals[b] - totals[a])],
                          lambda l, a=a, b=b: {"m1": phrasing.month(l, *a), "m2": phrasing.month(l, *b)}, category="trends", level="complex")
    return out


def evaluate(user, langs, rng) -> list:
    qs, out = _expenses(user), []
    if qs is None or not qs.exists():
        return out
    totals = _month_totals(qs)
    for a, b in _pairs(totals, 3):
        if totals[a] and totals[a] != totals[b]:
            out += expand(f"month_change_pct:{a[0]}-{a[1]:02d}:{b[0]}-{b[1]:02d}", "month_change_pct", rng, langs,
                          [money(totals[a]), money(totals[b]), percent(totals[b] - totals[a], totals[a])],
                          lambda l, a=a, b=b: {"m1": phrasing.month(l, *a), "m2": phrasing.month(l, *b)}, category="trends", level="complex", prefix="eval:")
    years = {}
    for r in qs.values("date__year").annotate(t=Sum("amount_base")):
        years[r["date__year"]] = dec(r["t"])
    for y1, y2 in zip(sorted(years), sorted(years)[1:]):
        if nonzero([years[y1], years[y2]]):
            out += expand(f"year_compare:{y1}:{y2}", "year_compare", rng, langs, [money(years[y1]), money(years[y2]), money(years[y2] - years[y1])],
                          lambda l, y1=y1, y2=y2: {"y1": y1, "y2": y2}, category="trends", level="complex", prefix="eval:")
    names = _categories(user)
    for y in sorted(years)[-1:]:
        for cid, name in list(names.items())[:12]:
            part = qs.filter(date__year=y, category_id=cid).aggregate(t=Sum("amount_base"))["t"]
            share = percent(part, years[y]) if part else None
            if share and dec(share) not in (0, 100):
                out += expand(f"cat_share:{cid}:{y}", "cat_share", rng, langs, [share], lambda l, n=name, y=y: {"category": n, "year": y},
                              category="trends", level="complex", prefix="eval:")
    subs = rows(user, "ExpenseSubcategory")
    sub_names = unique_names(subs) if subs is not None else {}
    for sid, name in list(sub_names.items())[:12]:
        agg = qs.filter(subcategory_id=sid).aggregate(t=Sum("amount_base"), c=Count("pk"))
        sub = subs.get(pk=sid)
        if agg["t"] and nonzero([agg["t"]]) and sub.category.name:
            out += expand(f"subcat:{sid}", "subcat", rng, langs, [money(agg["t"])], lambda l, n=name, c=sub.category.name: {"subcategory": n, "category": c},
                          category="expenses", prefix="eval:")
    return out
