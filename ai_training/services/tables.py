"""Table-based question kinds over every table the Agent may read (one table at a time): TRAIN kinds and EVAL kinds are different, so the
frozen test never repeats a training kind. Wording comes from phrasing (4 languages); figures from Django on the owner's own rows. A tie at
a cut-off, an all-zero answer or a label the app cannot translate means no question."""

from __future__ import annotations

from django.db import models
from django.db.models import Avg, Max, Min, Sum

from core.services.ai.investigation import scope

from . import phrasing, taxonomy
from .fam_util import expand, money, nonzero

TRAIN_KINDS = ("count", "total", "total_pc", "last_n", "month_total")
EVAL_KINDS = ("highest", "lowest", "average", "last_n", "in_year")
MAX_CURRENCIES = 6


def amounts(model):
    """Money-like fields only: Decimal with at most 2 decimals (rates, ratios and per-unit prices are skipped)."""
    return [f for f in scope.visible_fields(model) if isinstance(f, models.DecimalField) and not f.is_relation and f.decimal_places <= 2]


def dates(model):
    return [f for f in scope.visible_fields(model) if isinstance(f, (models.DateField, models.DateTimeField))]


def currency_path(model):
    for f in scope.visible_fields(model):
        if f.name == "currency" and f.is_relation and f.related_model and "code" in {x.name for x in f.related_model._meta.concrete_fields}:
            return "currency__code"
        if f.name in ("currency", "currency_code") and isinstance(f, models.CharField):
            return f.name
    return None


def _slots(model, **fixed):
    """Per-language slot builder: table label plus whichever of amount / date field labels were given."""
    def build(lang):
        out = {"label": phrasing.table_label(model, lang)}
        for slot, field in fixed.items():
            out[slot] = field if not hasattr(field, "verbose_name") else phrasing.field_label(field, lang)
        return out
    return build


def _make(info, kind, rng, langs, prefix, **parts):
    """Questions for one (table, kind): parts = intent, key, values, level and the slot fields."""
    model, cat = info.model, taxonomy.category_of(info.name)
    slots = {k: v for k, v in parts.items() if k not in ("intent", "key", "values", "level", "month_of")}
    month_of = parts.get("month_of")

    def build(lang):
        got = _slots(model, **slots)(lang)
        if month_of:
            got["month"] = phrasing.month(lang, *month_of)
        return got
    return expand(parts["key"], parts["intent"], rng, langs, parts["values"], build, category=cat, level=parts.get("level", "simple"), prefix=prefix)


def _ordered(qs, amount, date):
    return list(qs.exclude(**{f"{date.name}__isnull": True}).exclude(**{f"{amount.name}__isnull": True}).order_by(f"-{date.name}", "-pk"))


def _last_n(info, qs, amount, date, n, rng, langs, prefix):
    rows = _ordered(qs, amount, date)[: n + 1]
    if len(rows) <= n or getattr(rows[n - 1], date.name) == getattr(rows[n], date.name):
        return []
    values = [money(getattr(r, amount.name)) for r in rows[:n]]
    return _make(info, "last_n", rng, langs, prefix, intent="last_n", key=f"{info.name}:last{n}:{amount.name}:{date.name}", values=values,
                 level="intermediate", n=str(n), field=amount, datefield=date)


def train_cases(info, user, rng, langs) -> list:
    qs = scope.scoped_queryset(info, user)
    if info.scope is None or not qs.exists():
        return []
    name, cur, out = info.name, currency_path(info.model), []
    out += _make(info, "count", rng, langs, "", intent="count", key=f"{name}:count", values=[qs.count()])
    for amount in amounts(info.model):
        if cur:
            r = list(qs.values(cur).annotate(t=Sum(amount.name)).order_by(cur))
            if r and all(x["t"] is not None for x in r) and len(r) <= MAX_CURRENCIES:
                out += _make(info, "total_pc", rng, langs, "", intent="total_pc", key=f"{name}:sum_per_currency:{amount.name}",
                             values=[money(x["t"]) for x in r], level="intermediate", field=amount)
        else:
            total = qs.aggregate(t=Sum(amount.name))["t"]
            if total is not None:
                out += _make(info, "total", rng, langs, "", intent="total", key=f"{name}:sum:{amount.name}", values=[money(total)], field=amount)
        for date in dates(info.model)[:1]:
            out += _last_n(info, qs, amount, date, 3, rng, langs, "")
            ordered = _ordered(qs, amount, date)
            if ordered and not cur:
                latest = getattr(ordered[0], date.name)
                month = qs.filter(**{f"{date.name}__year": latest.year, f"{date.name}__month": latest.month}).aggregate(t=Sum(amount.name))["t"]
                if month is not None:
                    out += _make(info, "month_total", rng, langs, "", intent="month_total", key=f"{name}:month:{amount.name}:{date.name}:{latest.year}-{latest.month:02d}",
                                 values=[money(month)], level="intermediate", field=amount, datefield=date, month_of=(latest.year, latest.month))
    return [c for c in out if nonzero(c.expected["values"])]


def eval_cases(info, user, rng, langs) -> list:
    qs = scope.scoped_queryset(info, user)
    if info.scope is None or not qs.exists():
        return []
    name, cur, out = info.name, currency_path(info.model), []
    for amount in amounts(info.model):
        for kind, agg in (("max", Max), ("min", Min)):
            word = "highest" if kind == "max" else "lowest"
            if cur:
                r = list(qs.values(cur).annotate(v=agg(amount.name)).order_by(cur))
                if r and all(x["v"] is not None for x in r) and len(r) <= MAX_CURRENCIES:
                    out += _make(info, kind, rng, langs, "eval:", intent=f"{word}_pc", key=f"{name}:{kind}_per_currency:{amount.name}",
                                 values=[money(x["v"]) for x in r], level="intermediate", field=amount)
            else:
                v = qs.aggregate(v=agg(amount.name))["v"]
                if v is not None:
                    out += _make(info, kind, rng, langs, "eval:", intent=word, key=f"{name}:{kind}:{amount.name}", values=[money(v)], field=amount)
        if not cur and (avg := qs.aggregate(v=Avg(amount.name))["v"]) is not None:
            out += _make(info, "average", rng, langs, "eval:", intent="average", key=f"{name}:avg:{amount.name}", values=[money(avg)], field=amount)
        for date in dates(info.model)[:1]:
            out += _last_n(info, qs, amount, date, 5, rng, langs, "eval:")
    for date in dates(info.model)[:1]:
        newest = qs.exclude(**{f"{date.name}__isnull": True}).order_by(f"-{date.name}").values_list(date.name, flat=True).first()
        if newest is not None:
            count = qs.filter(**{f"{date.name}__year": newest.year}).count()
            if 0 < count < qs.count():
                out += _make(info, "in_year", rng, langs, "eval:", intent="in_year", key=f"{name}:in_year:{date.name}:{newest.year}", values=[count],
                             level="intermediate", datefield=date, year=newest.year)
    return [c for c in out if nonzero(c.expected["values"])]
