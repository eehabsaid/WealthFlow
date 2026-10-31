"""Category 16: vague questions where asking is the right answer. A question is generated only when the vagueness is REAL in the owner's data
(several months of expenses, several currencies, several salary rows), so "which one?" is a fair reply. Judged by the clarify judge."""

from __future__ import annotations

from ..fam_util import expand, rows


def _many(user, table, field, minimum=2) -> bool:
    qs = rows(user, table)
    return qs is not None and qs.values(field).distinct().count() >= minimum


def _make(key, intent, rng, langs, prefix=""):
    return expand(key, intent, rng, langs, [], lambda l: {"x": "y"}, category="ambiguous", level="simple", judge="clarify", prefix=prefix)


def train(user, langs, rng) -> list:
    out = []
    qs = rows(user, "Expense")
    if qs is not None and len({(d.year, d.month) for d in qs.dates("date", "month")}) >= 2:
        out += _make("amb_spend", "amb_spend", rng, langs)
    if _many(user, "BalanceEntry", "currency_id"):
        out += _make("amb_balance", "amb_balance", rng, langs)
    if _many(user, "SalaryEntry", "year") or _many(user, "SalaryEntry", "company_id"):
        out += _make("amb_salary", "amb_salary", rng, langs)
    return out


def evaluate(user, langs, rng) -> list:
    out = []
    if _many(user, "FixedAsset", "pk"):
        out += _make("amb_asset", "amb_asset", rng, langs, "eval:")
    out += _make("amb_compare", "amb_compare", rng, langs, "eval:") + _make("amb_save", "amb_save", rng, langs, "eval:")
    return out
