"""Questions from the live app. Tables come from the AI's own scope catalog (so only what the Agent may read), wording from each
model's labels, expected figures from Django queries on the owner's real rows. Only questions code can prove are produced; when
two rows tie at a cut-off the question is skipped (when in doubt, throw it out)."""

from __future__ import annotations

import calendar
import random
from dataclasses import dataclass, field
from decimal import Decimal

from django.db import models
from django.db.models import Sum

from core.services.ai.investigation import scope

LAST_N = 3
MAX_PER_MODEL = 6


@dataclass
class Case:
    key: str
    question: str
    expected: dict = field(default_factory=dict)


def _label(model) -> str:
    """"<verbose name> records": avoids the broken plurals Django makes for names without an explicit plural."""
    return f"{model._meta.verbose_name} records"


def _amounts(model):
    """Money-like fields only: a Decimal with at most 2 decimal places (rates, ratios and prices per unit carry more, so they are skipped)."""
    return [f for f in scope.visible_fields(model) if isinstance(f, models.DecimalField) and not f.is_relation and f.decimal_places <= 2]


def _dates(model):
    return [f for f in scope.visible_fields(model) if isinstance(f, (models.DateField, models.DateTimeField))]


def _currency_path(model):
    for f in scope.visible_fields(model):
        if f.name == "currency" and f.is_relation and f.related_model and "code" in {x.name for x in f.related_model._meta.concrete_fields}:
            return "currency__code"
        if f.name in ("currency", "currency_code") and isinstance(f, models.CharField):
            return f.name
    return None


def _num(value) -> str:
    return str(Decimal(str(value or 0)).quantize(Decimal("0.01")))


def cases_for(info, user) -> list[Case]:
    model, qs = info.model, scope.scoped_queryset(info, user)
    total = qs.count()
    if info.scope is None or not total:
        return []
    plural, name = _label(model), info.name
    out = [Case(f"{name}:count", f"How many {plural} do I have?", {"values": [total]})]
    cur = _currency_path(model)
    for amount in _amounts(model):
        label = str(amount.verbose_name)
        if cur:
            rows = list(qs.values(cur).annotate(t=Sum(amount.name)).order_by(cur))
            if rows and all(r["t"] is not None for r in rows) and len(rows) <= 6:
                out.append(Case(f"{name}:sum_per_currency:{amount.name}", f"What is the total {label} of my {plural} per currency?",
                                {"values": [_num(r["t"]) for r in rows]}))
        else:
            value = qs.aggregate(t=Sum(amount.name))["t"]
            if value is not None:
                out.append(Case(f"{name}:sum:{amount.name}", f"What is the total {label} of my {plural}?", {"values": [_num(value)]}))
        for date in _dates(model)[:1]:
            out += _dated(qs, plural, name, amount, date, cur)
    return out


def _dated(qs, plural, name, amount, date, cur) -> list[Case]:
    ordered = list(qs.exclude(**{f"{date.name}__isnull": True}).exclude(**{f"{amount.name}__isnull": True}).order_by(f"-{date.name}", "-pk"))
    out = []
    if len(ordered) > LAST_N and getattr(ordered[LAST_N - 1], date.name) != getattr(ordered[LAST_N], date.name):
        values = [_num(getattr(r, amount.name)) for r in ordered[:LAST_N]]
        out.append(Case(f"{name}:last{LAST_N}:{amount.name}:{date.name}", f"Show my last {LAST_N} {plural} by {date.verbose_name} with their {amount.verbose_name}.",
                        {"values": values}))
    if ordered and not cur:
        latest = getattr(ordered[0], date.name)
        month = qs.filter(**{f"{date.name}__year": latest.year, f"{date.name}__month": latest.month}).aggregate(t=Sum(amount.name))["t"]
        if month is not None:
            out.append(Case(f"{name}:month:{amount.name}:{date.name}:{latest.year}-{latest.month:02d}",
                            f"What is the total {amount.verbose_name} of my {plural} in {calendar.month_name[latest.month]} {latest.year}, by {date.verbose_name}?",
                            {"values": [_num(month)]}))
    return out


def generate(user, *, limit: int = 0, seed: int | None = None) -> list[Case]:
    """All provable cases for `user`, at most MAX_PER_MODEL per table; `limit` samples that many (seeded, repeatable)."""
    rng, cases = random.Random(seed), []
    for info in scope.catalog().values():
        found = cases_for(info, user)
        rng.shuffle(found)
        cases += found[:MAX_PER_MODEL]
    cases.sort(key=lambda c: c.key)
    if limit and len(cases) > limit:
        cases = sorted(rng.sample(cases, limit), key=lambda c: c.key)
    return cases
