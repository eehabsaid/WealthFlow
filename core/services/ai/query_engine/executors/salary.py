"""Salary capability: paid / expected / bonus / total / average / latest, by month or company. Owner scope: company__owner."""

from __future__ import annotations

from typing import Any

from ..labels import month_label, range_label, t
from ..spec import Capability, Metric, QueryRequest, QueryResult, Row
from .common import home_currency, money

_TERMS = (
    (r"\bsalar(?:y|ies)\b|\bpay ?slips?\b|\bpay ?checks?\b|\bwages?\b|\btake[- ]home\b|\bmy pay\b|\bpaid me\b|\bget paid\b|\bearnings?\b", 3),
    (r"راتب\w*|رواتب|مرتب\w*|معاش\w*|ماهيه|ماهيتي", 3),
    (r"\bbonus(?:es)?\b|مكافا\w*", 3),
)
_METRICS = (
    Metric("bonus", (r"\bbonus(?:es)?\b", r"مكافا\w*")),
    Metric("expected", (r"\bexpected\b|\bsupposed\b|\bgross\b", r"المتوقع|متوقع")),
    Metric("average", (r"\b(?:average|avg|mean)\b", r"متوسط|معدل")),
    Metric("total", (r"\b(?:total|sum|overall|altogether|combined)\b", r"اجمالي|مجموع|المجموع")),
    Metric("latest", (r"\b(?:latest|last|most recent|newest|current)\b", r"اخر|احدث|الحالي|حاليا")),
    Metric("paid"),
)
_DIMS = (
    ("company", (r"\b(?:by|per|each|every)\s+company\b|\bcompan(?:y|ies)\b", r"حسب (?:ال)?شركه|لكل شركه|الشركات")),
    ("month", (r"\b(?:by month|per month|monthly|month by month|each month)\b", r"شهريا|حسب الشهر|لكل شهر|كل شهر")),
)
_WHAT = {"paid": "what_paid", "expected": "what_expected", "bonus": "what_bonus", "total": "what_paid", "average": "what_paid", "latest": "what_paid"}


def _entries(user: Any, months: list[tuple[int, int]]) -> list[tuple[int, int, Any]]:
    from core.models import SalaryEntry
    from core.services.ai.providers.salary_provider.constants import MONTH_NAME_TO_INT

    qs = SalaryEntry.objects.filter(company__owner=user).select_related("company")
    if months:
        qs = qs.filter(year__in={y for y, _ in months})
    rows = [(e.year, MONTH_NAME_TO_INT.get(str(e.month or "").strip().lower(), 0), e) for e in qs]
    if months:
        wanted = set(months)
        rows = [r for r in rows if (r[0], r[1]) in wanted]
    return sorted(rows, key=lambda r: (r[0], r[1], r[2].id))


def _val(e: Any, metric: str) -> float:
    return float(getattr(e, {"expected": "expected", "bonus": "bonus"}.get(metric, "paid")) or 0)


def run(user: Any, req: QueryRequest) -> QueryResult:
    lang, cur, months = req.lang, home_currency(user), list(req.periods)
    rows = _entries(user, months)
    metric = req.metric if req.metric in _WHAT else "paid"
    if not months:  # 'latest' with no period
        if not rows:
            return QueryResult(intro=t(lang, "sal_none_any"))
        y, _, e = rows[-1]
        return QueryResult(intro=t(lang, "sal_latest", amount=money(float(e.paid or 0), cur), month=e.month, year=y,
                                   company=e.company.name if e.company else ""), facts={"paid": float(e.paid or 0)})
    label = range_label(lang, months)
    if not rows:
        return QueryResult(intro=t(lang, "sal_none", label=label))
    what = t(lang, _WHAT[metric])
    if len(months) == 1 and metric != "average":
        if metric in ("paid", "latest"):
            parts = "; ".join(t(lang, "sal_part", amount=money(_val(e, "paid"), cur), company=e.company.name if e.company else "") for _, _, e in rows)
            return QueryResult(intro=t(lang, "sal_month", label=label, parts=parts), facts={"paid": sum(_val(e, "paid") for *_, e in rows)})
        return QueryResult(intro=t(lang, "sal_total", what=what, label=label, amount=money(sum(_val(e, metric) for *_, e in rows), cur)))
    if metric == "average":
        active = {(y, m) for y, m, _ in rows}
        total = sum(_val(e, "paid") for *_, e in rows)
        return QueryResult(intro=t(lang, "sal_avg", what=what, label=label, amount=money(total / len(active), cur), n=len(active)),
                           facts={"average": total / len(active), "months": len(active)})
    if metric == "total":
        total = sum(_val(e, "paid") for *_, e in rows)
        return QueryResult(intro=t(lang, "sal_total", what=what, label=label, amount=money(total, cur)), facts={"total": total})
    out, sums = [], [0.0, 0.0, 0.0]
    for y, m, e in rows:
        vals = [_val(e, "expected"), _val(e, "paid"), _val(e, "bonus")]
        sums = [a + b for a, b in zip(sums, vals)]
        out.append(Row([month_label(lang, y, m, abbr=True), e.company.name if e.company else "", *(money(x, cur) for x in vals)]))
    out.append(Row([t(lang, "grand"), "", *(money(x, cur) for x in sums)], bold=True))
    return QueryResult(intro=t(lang, "sal_table", label=label, cur=cur), rows=out,
                       columns=[t(lang, "col_month"), t(lang, "col_company"), t(lang, "col_expected"), t(lang, "col_paid"), t(lang, "col_bonus")],
                       facts={"groups": {f"{y}-{m:02d}": _val(e, "paid") for y, m, e in rows}, "total": sums[1], "currency": cur})


CAPABILITIES = (Capability(
    key="salary", provider_key="salary", label="Salary", terms=_TERMS, metrics=_METRICS, default_metric="paid",
    dimensions=_DIMS, filters=(), time="required", follow_subject="salary", executor=run, sources=("salary",), latest_metrics=("latest", "paid"),
),)
