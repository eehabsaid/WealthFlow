"""Categories 3, 7 and 12 (salary against expenses). Only when every salary row is in the user's base currency and has a numeric month, so
the 'salary paid' and 'expenses' figures are comparable (when in doubt, throw it out). Salary paid = the `paid` column."""

from __future__ import annotations

from collections import defaultdict

from django.db.models import Sum

from core.services.shared.base_currency import get_user_base_code

from .. import phrasing
from ..fam_util import dec, expand, money, nonzero, percent, rows


def _salary_by_month(user) -> dict:
    sal, companies = rows(user, "SalaryEntry"), rows(user, "Company")
    if sal is None or companies is None:
        return {}
    base = str(get_user_base_code(user) or "").upper()
    used = set(sal.values_list("company_id", flat=True))
    if any(str(c.current_salary_currency.code if c.current_salary_currency else "").upper() != base for c in companies.filter(pk__in=used).select_related("current_salary_currency")):
        return {}
    out = defaultdict(lambda: dec(0))
    for e in sal.exclude(paid__isnull=True):
        if str(e.month).isdigit() and 1 <= int(e.month) <= 12:
            out[(int(e.year), int(e.month))] += dec(e.paid)
    return out


def _expense_months(user) -> dict:
    qs = rows(user, "Expense")
    if qs is None:
        return {}
    return {(r["date__year"], r["date__month"]): dec(r["t"]) for r in qs.exclude(amount_base__isnull=True).values("date__year", "date__month").annotate(t=Sum("amount_base"))}


def _both(user):
    salary, spent = _salary_by_month(user), _expense_months(user)
    return salary, spent, sorted(k for k in salary if k in spent and salary[k] > 0)


def train(user, langs, rng) -> list:
    salary, spent, months = _both(user)
    out = []
    for y, m in months[-3:]:
        diff = salary[(y, m)] - spent[(y, m)]
        if nonzero([diff]):
            out += expand(f"month_net:{y}-{m:02d}", "month_net", rng, langs, [money(diff)], lambda l, y=y, m=m: {"month": phrasing.month(l, y, m)},
                          category="cash_flow", level="complex")
    for y in sorted({k[0] for k in months})[-2:]:
        ms = [k for k in months if k[0] == y]
        diff = sum((salary[k] - spent[k] for k in ms), dec(0))
        if len(ms) >= 2 and nonzero([diff]):
            out += expand(f"savings_year:{y}", "savings_year", rng, langs, [money(diff)], lambda l, y=y: {"year": y}, category="cross", level="complex")
    return out


def evaluate(user, langs, rng) -> list:
    salary, spent, months = _both(user)
    out = []
    for y in sorted({k[0] for k in months})[-2:]:
        ms = [k for k in months if k[0] == y]
        earned, used = sum((salary[k] for k in ms), dec(0)), sum((spent[k] for k in ms), dec(0))
        share = percent(used, earned)
        if len(ms) >= 2 and share and nonzero([share]):
            out += expand(f"expense_salary:{y}", "expense_salary", rng, langs, [share], lambda l, y=y: {"year": y}, category="cross", level="complex", prefix="eval:")
    return out
