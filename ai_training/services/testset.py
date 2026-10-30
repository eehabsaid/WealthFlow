"""The fixed test set for comparing two models: questions from the live data that training never used.

Training questions (generator.py) are: count, total, total per currency, last 3, month total. These are other kinds: highest, lowest,
average, last 5, count in a year. Keys start with "eval:", so a test question can never be a training question. Same rules as the
training questions: wording from the model labels, expected figures computed by Django from the owner's own rows, anything with a tie
at a cut-off is skipped. A fixed seed gives the same questions every time (as long as the data is the same)."""

from __future__ import annotations

import random
from decimal import Decimal

from django.db.models import Avg, Max, Min

from core.services.ai.investigation import scope

from .generator import Case, _amounts, _currency_path, _dates, _label, _num

PER_TABLE = 4
LAST_N = 5


def _extremes(qs, plural, name, amount, cur) -> list[Case]:
    out, label = [], str(amount.verbose_name)
    for kind, agg, word in (("max", Max, "highest"), ("min", Min, "lowest")):
        if cur:
            rows = list(qs.values(cur).annotate(v=agg(amount.name)).order_by(cur))
            if rows and all(r["v"] is not None for r in rows) and len(rows) <= 6:
                out.append(Case(f"eval:{name}:{kind}_per_currency:{amount.name}", f"What is the {word} {label} among my {plural}, per currency?",
                                {"values": [_num(r["v"]) for r in rows]}))
            continue
        value = qs.aggregate(v=agg(amount.name))["v"]
        if value is not None:
            out.append(Case(f"eval:{name}:{kind}:{amount.name}", f"What is the {word} {label} among my {plural}?", {"values": [_num(value)]}))
    return out


def _average(qs, plural, name, amount, cur) -> list[Case]:
    """Per-currency averages are skipped: only a single-currency average is one clear figure."""
    value = None if cur else qs.aggregate(v=Avg(amount.name))["v"]
    if value is None:
        return []
    return [Case(f"eval:{name}:avg:{amount.name}", f"What is the average {amount.verbose_name} of my {plural}?", {"values": [_num(value)]})]


def _last_n(qs, plural, name, amount, date) -> list[Case]:
    ordered = list(qs.exclude(**{f"{date.name}__isnull": True}).exclude(**{f"{amount.name}__isnull": True}).order_by(f"-{date.name}", "-pk")[:LAST_N + 1])
    if len(ordered) <= LAST_N or getattr(ordered[LAST_N - 1], date.name) == getattr(ordered[LAST_N], date.name):
        return []   # fewer rows than asked, or a tie at the cut-off: skipped
    return [Case(f"eval:{name}:last{LAST_N}:{amount.name}:{date.name}",
                 f"Show my last {LAST_N} {plural} by {date.verbose_name} with their {amount.verbose_name}.",
                 {"values": [_num(getattr(r, amount.name)) for r in ordered[:LAST_N]]})]


def _in_year(qs, plural, name, date) -> list[Case]:
    newest = qs.exclude(**{f"{date.name}__isnull": True}).order_by(f"-{date.name}").values_list(date.name, flat=True).first()
    if newest is None:
        return []
    count = qs.filter(**{f"{date.name}__year": newest.year}).count()
    if not 0 < count < qs.count():   # all rows in that year would make the question too easy to guess
        return []
    return [Case(f"eval:{name}:in_year:{date.name}:{newest.year}", f"How many of my {plural} have a {date.verbose_name} in {newest.year}?", {"values": [count]})]


def cases_for(info, user) -> list[Case]:
    model, qs = info.model, scope.scoped_queryset(info, user)
    if info.scope is None or not qs.count():
        return []
    plural, name, cur, out = _label(model), info.name, _currency_path(model), []
    dates = _dates(model)[:1]
    for amount in _amounts(model):
        out += _extremes(qs, plural, name, amount, cur) + _average(qs, plural, name, amount, cur)
        for date in dates:
            out += _last_n(qs, plural, name, amount, date)
    for date in dates:
        out += _in_year(qs, plural, name, date)
    return [c for c in out if any(Decimal(str(v)) != 0 for v in c.expected["values"])]   # an all-zero answer proves nothing: skipped


def build(user, *, limit: int, seed: int) -> list[Case]:
    """At most PER_TABLE questions per table, then `limit` of them (seeded sample), sorted by key."""
    rng, cases = random.Random(seed), []
    for info in scope.catalog().values():
        found = cases_for(info, user)
        rng.shuffle(found)
        cases += found[:PER_TABLE]
    cases.sort(key=lambda c: c.key)
    if limit and len(cases) > limit:
        cases = sorted(rng.sample(cases, limit), key=lambda c: c.key)
    return cases

