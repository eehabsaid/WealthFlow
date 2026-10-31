"""Category 11, numeric what-ifs only: the hypothetical percentage / amount is in the question, the base figure is the owner's real total, so
code can prove the resulting figures (not the reasoning around them)."""

from __future__ import annotations

import math
from collections import defaultdict

from django.db.models import Sum

from .. import phrasing
from ..fam_util import dec, expand, money, nonzero, rows, unique_names

PCTS = (10, 15, 20, 25)
EXTRAS = (100, 250, 500, 1000, 2500, 5000, 10000)


def _expenses(user):
    qs = rows(user, "Expense")
    return qs.exclude(amount_base__isnull=True) if qs is not None else None


def train(user, langs, rng) -> list:
    qs, out = _expenses(user), []
    if qs is None or not qs.exists():
        return out
    cats = rows(user, "ExpenseCategory")
    for cid, name in (unique_names(cats) if cats is not None else {}).items():
        by_year = defaultdict(lambda: dec(0))
        for r in qs.filter(category_id=cid).values("date__year").annotate(t=Sum("amount_base")):
            by_year[r["date__year"]] += dec(r["t"])
        for y in sorted(by_year)[-1:]:
            pct = rng.choice(PCTS)
            saved = by_year[y] * pct / 100
            if nonzero([saved]):
                out += expand(f"whatif_cut_year:{cid}:{y}:{pct}", "whatif_cut_year", rng, langs, [money(saved), money(by_year[y] - saved)],
                              lambda l, n=name, y=y, p=pct: {"category": n, "year": y, "pct": p}, category="what_if", level="complex")
    for r in list(qs.values("date__year", "date__month").annotate(t=Sum("amount_base")).order_by("-date__year", "-date__month")[:3]):
        y, m, total, pct = r["date__year"], r["date__month"], dec(r["t"]), rng.choice(PCTS)
        if nonzero([total]):
            out += expand(f"whatif_cut_month:{y}-{m:02d}:{pct}", "whatif_cut_month", rng, langs, [money(total * (100 - pct) / 100), money(total * pct / 100)],
                          lambda l, y=y, m=m, p=pct: {"month": phrasing.month(l, y, m), "pct": p}, category="what_if", level="complex")
    return out


def evaluate(user, langs, rng) -> list:
    qs, out = _expenses(user), []
    if qs is not None:
        for r in list(qs.values("date__year").annotate(t=Sum("amount_base")).order_by("-date__year")[:2]):
            y, total, pct = r["date__year"], dec(r["t"]), rng.choice(PCTS)
            if nonzero([total]):
                out += expand(f"whatif_raise:{y}:{pct}", "whatif_raise", rng, langs, [money(total * (100 + pct) / 100)],
                              lambda l, y=y, p=pct: {"year": y, "pct": p}, category="what_if", level="complex", prefix="eval:")
    goals = rows(user, "Goal")
    for gid, name in (unique_names(goals) if goals is not None else {}).items():
        g = goals.get(pk=gid)
        left = dec(g.target_amount) - dec(g.current_saved_amount)
        extra = next((e for e in EXTRAS if left > 0 and 3 <= math.ceil(left / e) <= 60), None)
        if extra:
            out += expand(f"whatif_goal:{gid}:{extra}", "whatif_goal", rng, langs, [math.ceil(left / extra)],
                          lambda l, n=name, e=extra: {"goal": n, "extra": e}, category="what_if", level="complex", prefix="eval:")
    return out
