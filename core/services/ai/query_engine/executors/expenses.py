"""Expenses capability: total / list / latest / top / average, by month | category | day, optional category filter."""

from __future__ import annotations

from typing import Any

from ..labels import range_label, t
from ..spec import Capability, Metric, QueryRequest, QueryResult
from . import expense_views as v
from .common import cell, home_currency, money

_TERMS = (
    (r"\bexpens\w*|\bspen[dt]\w*|\bspending\b|\boutgoings?\b|\bpurchases?\b|\bbills?\b", 3),
    (r"مصروف\w*|مصاريف\w*|انفاق|انفقت|صرفت|نفقات|مشتريات|صرفي", 3),
    (r"\btransactions?\b|معاملات", 3),
)
_METRICS = (
    Metric("latest", (r"\b(?:last|latest|most recent|newest|recent)\s+(?:\d+\s+)?(?:expenses?|transactions?|purchases?|payments?|spend\w*)\b",
                      r"\bmy (?:last|latest)\b", r"(?:اخر|احدث)\s*(?:\d+\s*)?(?:مصروف\w*|معامله|معاملات|عمليه|عمليات|مشتريات)")),
    Metric("top", (r"\b(?:biggest|largest|highest|most expensive|top)\b", r"اكبر|اعلي|اغلي")),
    Metric("average", (r"\b(?:average|avg|mean)\b", r"متوسط|معدل")),
    Metric("list", (r"\b(?:table|tabular|detail(?:s|ed)?|itemi[sz]ed|list|transactions|organi[sz]ed|breakdown|each expense|all (?:my )?expenses)\b",
                    r"جدول|تفاصيل|تفصيل|قايمه|كل المصروفات|كل معاملات|مفصل")),
    Metric("total"),
)
_DIMS = (
    ("category", (r"\b(?:by|per|each|every)\s+categor\w*|\bcategor(?:y|ies)\b", r"حسب (?:ال)?(?:فئه|تصنيف|فئات)|لكل فئه|فئات|تصنيف|بالفئه|بالتصنيف")),
    ("day", (r"\b(?:daily|per day|by day|each day|every day|day by day|day-by-day|day wise)\b", r"يوميا|يومي|كل يوم|حسب اليوم|لكل يوم")),
    ("month", (r"\b(?:by month|per month|monthly|month by month|each month|every month|month wise)\b", r"شهريا|شهري|حسب الشهر|لكل شهر|كل شهر")),
)


def _n(req: QueryRequest, default: int, cap: int = 50) -> int:
    return max(1, min(req.n or default, cap))


def run(user: Any, req: QueryRequest) -> QueryResult:
    lang, cur, months = req.lang, home_currency(user), list(req.periods)
    cat = str(req.filters.get("category") or "")
    if req.metric == "latest":
        qs = v.base_qs(user, months, cat).order_by("-date", "-id")
        n = _n(req, 1)
        rows = v.item_rows(lang, qs[:n], cur)
        if not rows:
            return QueryResult(intro=t(lang, "exp_none", label="—"))
        return QueryResult(intro=t(lang, "exp_latest", n=len(rows), cur=cur),
                           columns=[t(lang, "col_date"), t(lang, "col_category"), t(lang, "col_desc"), t(lang, "col_amount")],
                           rows=rows, facts={"count": len(rows)})
    if not months:
        return QueryResult(intro=t(lang, "exp_none", label="—"))
    qs = v.base_qs(user, months, cat)
    label = range_label(lang, months)
    if req.metric == "top":
        if req.group_by == "category":
            cats = v.cat_totals(qs)
            if not cats:
                return QueryResult(intro=t(lang, "exp_none", label=label))
            (name,), (amt, _) = max(cats.items(), key=lambda x: x[1][0])
            total = sum(x[0] for x in cats.values())
            return QueryResult(intro=t(lang, "exp_top_cat", label=label, name=cell(name or t(lang, "uncategorized")), amount=money(amt, cur),
                                       share=f"{amt / total * 100:.1f}%"), facts={"top_category": name, "amount": amt})
        rows = v.item_rows(lang, qs.order_by("-amount_base", "-id")[:_n(req, 1)], cur)
        if not rows:
            return QueryResult(intro=t(lang, "exp_none", label=label))
        return QueryResult(intro=t(lang, "exp_top", n=len(rows), label=label, cur=cur), rows=rows,
                           columns=[t(lang, "col_date"), t(lang, "col_category"), t(lang, "col_desc"), t(lang, "col_amount")])
    totals = v.month_totals(qs)
    grand = sum(x[0] for x in totals.values())
    count = sum(x[1] for x in totals.values())
    if req.metric == "average":
        active = [k for k, x in totals.items() if x[1]]
        if not active:
            return QueryResult(intro=t(lang, "exp_none", label=label))
        return QueryResult(intro=t(lang, "exp_avg", label=label, amount=money(grand / len(active), cur), n=len(active)),
                           facts={"average": grand / len(active), "months": len(active), "currency": cur})
    group = req.group_by
    if group == "category":
        cats = v.cat_totals(qs, by_month=len(months) > 1)
        return v.category_single(lang, months[0], cats, cur) if len(months) == 1 else v.category_multi(lang, months, cats, cur)
    if group == "day":
        return v.daily(lang, months, qs, cur)
    if req.metric == "list":
        return v.transactions(lang, months, qs, totals, cur)
    if len(months) == 1:
        return v.total_sentence(lang, months, grand, count, cur, cat)
    return v.by_month(lang, months, totals, cur)


CAPABILITIES = (Capability(
    key="expenses", provider_key="expenses", label="Expenses", terms=_TERMS, metrics=_METRICS, default_metric="total",
    dimensions=_DIMS, filters=("category",), time="required", executor=run, sources=("expenses",), latest_metrics=("latest",),
),)
