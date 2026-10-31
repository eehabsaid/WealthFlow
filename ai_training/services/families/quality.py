"""Category 14: data quality. Code finds the real issues in the owner's expense rows (counted, never listed with private text); the question
asks how many. Counts of zero are skipped (nothing to prove)."""

from __future__ import annotations

from datetime import date

from django.db.models import Count

from ..fam_util import expand, rows


def _qs(user):
    return rows(user, "Expense")


def _one(user, langs, rng, key, intent, count, total, prefix=""):
    if count and count < total:
        return expand(key, intent, rng, langs, [count], lambda l: {"x": "y"}, category="quality", prefix=prefix)
    return []


def train(user, langs, rng) -> list:
    qs = _qs(user)
    if qs is None or not qs.exists():
        return []
    total = qs.count()
    groups = qs.values("date", "amount_base", "category_id").annotate(c=Count("pk")).filter(c__gt=1)
    dupes = sum(g["c"] for g in groups)
    return (_one(user, langs, rng, "q_nosub", "q_nosub", qs.filter(subcategory__isnull=True).count(), total)
            + _one(user, langs, rng, "q_dupes", "q_dupes", dupes, total + 1))


def evaluate(user, langs, rng) -> list:
    qs = _qs(user)
    if qs is None or not qs.exists():
        return []
    total = qs.count()
    return (_one(user, langs, rng, "q_nonpos", "q_nonpos", qs.filter(amount_base__lte=0).count(), total, "eval:")
            + _one(user, langs, rng, "q_future", "q_future", qs.filter(date__gt=date.today()).count(), total, "eval:")
            + _one(user, langs, rng, "q_nobank", "q_nobank", qs.filter(bank__isnull=True).count(), total, "eval:"))
