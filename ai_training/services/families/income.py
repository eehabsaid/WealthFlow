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


def _yearly_income(user) -> dict:
    salary, companies = rows(user, "SalaryEntry"), rows(user, "Company")
    if salary is None or companies is None:
        return {}
    base = str(get_user_base_code(user) or "").upper()
    used = set(salary.values_list("company_id", flat=True))
    if any(
        str(c.current_salary_currency.code if c.current_salary_currency else "").upper() != base
        for c in companies.filter(pk__in=used).select_related("current_salary_currency")
    ):
        return {}

    by_year = defaultdict(lambda: {"salary": dec(0), "bonus": dec(0), "per_diem": dec(0), "rent": dec(0)})
    for r in salary.exclude(paid__isnull=True).values("year").annotate(paid=Sum("paid"), bonus=Sum("bonus")):
        by_year[r["year"]]["salary"] += dec(r["paid"])
        by_year[r["year"]]["bonus"] += dec(r["bonus"])

    per_diem = rows(user, "PerDiem")
    if per_diem is not None:
        for r in per_diem.exclude(amount_base__isnull=True).values("date__year").annotate(total=Sum("amount_base")):
            by_year[r["date__year"]]["per_diem"] += dec(r["total"])

    receipts = rows(user, "RentReceipt")
    if receipts is not None:
        receipts = receipts.filter(rental__asset__owner=user)
        if receipts.exclude(currency__code__iexact=base).exists():
            return {}
        for r in receipts.values("received_date__year").annotate(total=Sum("amount")):
            by_year[r["received_date__year"]]["rent"] += dec(r["total"])

    return {
        year: (
            values["salary"], values["bonus"], values["per_diem"], values["rent"],
            sum(values.values(), dec(0)),
        )
        for year, values in by_year.items()
    }


def _salary_remaining_by_year(user) -> dict:
    salary, companies = rows(user, "SalaryEntry"), rows(user, "Company")
    if salary is None or companies is None:
        return {}
    base = str(get_user_base_code(user) or "").upper()
    used = set(salary.values_list("company_id", flat=True))
    if any(
        str(c.current_salary_currency.code if c.current_salary_currency else "").upper() != base
        for c in companies.filter(pk__in=used).select_related("current_salary_currency")
    ):
        return {}
    remaining = defaultdict(lambda: dec(0))
    for row in salary.exclude(expected__isnull=True).exclude(paid__isnull=True).values("year", "expected", "paid"):
        remaining[row["year"]] += max(dec(0), dec(row["expected"]) - dec(row["paid"]))
    return dict(remaining)


def _other_income_by_year(user) -> dict:
    per_diem, receipts = rows(user, "PerDiem"), rows(user, "RentReceipt")
    if per_diem is None or receipts is None:
        return {}
    base = str(get_user_base_code(user) or "").upper()
    receipts = receipts.filter(rental__asset__owner=user)
    if receipts.exclude(currency__code__iexact=base).exists():
        return {}

    totals = defaultdict(lambda: {"per_diem": dec(0), "rent": dec(0)})
    for r in per_diem.exclude(amount_base__isnull=True).values("date__year").annotate(total=Sum("amount_base")):
        totals[r["date__year"]]["per_diem"] += dec(r["total"])
    for r in receipts.values("received_date__year").annotate(total=Sum("amount")):
        totals[r["received_date__year"]]["rent"] += dec(r["total"])
    return {
        year: (values["per_diem"], values["rent"], values["per_diem"] + values["rent"])
        for year, values in totals.items()
    }


def _expense_years(user) -> dict:
    expenses = rows(user, "Expense")
    if expenses is None:
        return {}
    return {
        r["date__year"]: dec(r["total"])
        for r in expenses.exclude(amount_base__isnull=True).values("date__year").annotate(total=Sum("amount_base"))
    }


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

    yearly_income = _yearly_income(user)
    for year, (paid, bonus, per_diem, rent, total) in yearly_income.items():
        if nonzero([paid, bonus, per_diem, rent]):
            out += expand(
                f"income_stream_year:{year}", "income_stream_year", rng, langs,
                [money(paid), money(bonus), money(per_diem), money(rent), money(total)],
                lambda l, y=year: {"year": y}, category="income", level="complex",
            )

    expenses = _expense_years(user)
    for year, income_parts in yearly_income.items():
        if year not in expenses:
            continue
        income_total, spent_total = income_parts[-1], expenses[year]
        net = income_total - spent_total
        if nonzero([income_total, spent_total, net]):
            out += expand(
                f"income_net_year:{year}", "income_net_year", rng, langs,
                [money(income_total), money(spent_total), money(net)],
                lambda l, y=year: {"year": y}, category="cross", level="complex",
            )

    if not yearly_income:
        for year, (per_diem, rent, total) in _other_income_by_year(user).items():
            if nonzero([per_diem, rent]):
                out += expand(
                    f"other_income_year:{year}", "other_income_year", rng, langs,
                    [money(per_diem), money(rent), money(total)],
                    lambda l, y=year: {"year": y}, category="income", level="complex",
                )
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

    for year, remaining in _salary_remaining_by_year(user).items():
        if nonzero([remaining]):
            out += expand(
                f"salary_remaining_year:{year}", "salary_remaining_year", rng, langs, [money(remaining)],
                lambda l, y=year: {"year": y}, category="income", level="intermediate", prefix="eval:",
            )
    return out
