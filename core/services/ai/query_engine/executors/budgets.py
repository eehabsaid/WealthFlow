"""Budgets and recurring transactions: instant, owner-scoped answers (0 LLM calls).

Budget spend is BudgetService.compute_spent (Expense.amount_base, in the user's base currency), so every
figure here is in the user's own currency and no currency is hardcoded. Recurring amounts are shown in the
item's own currency; the monthly total converts each item to the user's base currency.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from ..labels import t
from ..lexicon import norm
from ..spec import Capability, Metric, QueryRequest, QueryResult, Row
from .common import MAX_ROWS, cell, home_currency, money

_BUDGET_TERMS = (
    (r"\bbudgets?\b|\bover ?budget\b|\bunder ?budget\b|\bspending (?:limit|cap)s?\b|\bspend(?:ing)? limits?\b", 8),
    (r"ميزاني\w*|حد (?:ال)?(?:انفاق|مصروفات|صرف)", 8),
)
_RECURRING_TERMS = (
    (r"\brecurring\b|\bsubscriptions?\b|\bautopay\b|\bstanding orders?\b|\bdirect debits?\b|\bscheduled (?:payments?|bills?|expenses?)\b|"
     r"\b(?:upcoming|coming|due|monthly|regular|fixed) (?:bills?|payments?)\b|\bbills? (?:are |is )?coming(?: up)?\b|\bbills? due\b|\b(?:due|upcoming|next) bills?\b|\bbills? (?:due|coming|this month|next)\b|\brepeat(?:ing)? (?:expenses?|payments?)\b", 8),
    (r"متكرر\w*|اشتراك\w*|دفعات دوري\w*|مدفوعات دوري\w*|فواتير (?:قادم\w*|الشهر|مستحق\w*)|التزام\w* (?:شهري\w*|ثابت\w*)|التزامات\w*|مصروفات ثابت\w*", 8),
)
_UPCOMING_DAYS = 30
_MONTHLY_FACTOR = {"daily": Decimal("30"), "weekly": Decimal("52") / Decimal("12"), "monthly": Decimal("1"), "yearly": Decimal("1") / Decimal("12")}


def _not_current(req: QueryRequest) -> bool:
    """Budgets/recurring items describe NOW. "this month" is fine; another month would be answered with
    today's figures, so it is refused (history of budget spend is not stored per month)."""
    today = date.today()
    return any(p != (today.year, today.month) for p in req.periods)


def _pct(x: float) -> str:
    return f"{x:,.1f}%"


def _budgets(user: Any, req: QueryRequest) -> list[dict[str, Any]]:
    from core.services.budgets.budget_service import BudgetService

    rows = [b for b in BudgetService.list_with_spend(user) if b.get("is_active", True)]
    wanted = norm(str(req.filters.get("category") or ""))
    if wanted:
        rows = [b for b in rows if norm(b.get("category_name") or "") == wanted or norm(b.get("name") or "") == wanted]
    return rows


def run_budgets(user: Any, req: QueryRequest) -> QueryResult:
    lang, cur = req.lang, home_currency(user)
    if _not_current(req):
        return QueryResult(intro=t(lang, "only_current"))
    rows = _budgets(user, req)
    label = str(req.filters.get("category") or "")
    if not rows:
        return QueryResult(intro=t(lang, "bud_none_cat", cat=label) if label else t(lang, "bud_none"))
    over = [b for b in rows if b["percent_used"] >= 100]
    near = [b for b in rows if b["percent_used"] >= b["alert_threshold_percent"] and b["percent_used"] < 100]
    if req.metric == "over":
        flagged = over + near
        if not flagged:
            return QueryResult(intro=t(lang, "bud_all_ok", n=len(rows)), facts={"over": 0, "near": 0})
        rows = flagged
        intro = t(lang, "bud_over", over=len(over), near=len(near), cur=cur)
    elif req.metric == "remaining":
        intro = t(lang, "bud_remaining", cur=cur, amount=money(sum(max(b["remaining_base"], 0) for b in rows), cur))
    else:
        intro = t(lang, "bud_status", n=len(rows), cur=cur)
    table = [Row([cell(b["name"]), cell(b["category_name"] or t(lang, "bud_all_cats")), t(lang, f"per_{b['period']}"),
                  f"{b['amount_base']:,.2f}", f"{b['spent_base']:,.2f}", f"{b['remaining_base']:,.2f}", _pct(b["percent_used"])])
             for b in rows[:MAX_ROWS]]
    cols = [t(lang, "col_name"), t(lang, "col_category"), t(lang, "col_period"), t(lang, "col_limit"),
            t(lang, "col_spent"), t(lang, "col_left"), t(lang, "col_used")]
    return QueryResult(intro=intro, columns=cols, rows=table,
                       facts={"budgets": len(rows), "over": len(over), "near": len(near),
                              "spent": sum(b["spent_base"] for b in rows), "limit": sum(b["amount_base"] for b in rows)})


def _monthly_base(rec: Any, base: str) -> Decimal | None:
    from core.services.shared.currency_conversion_service import CurrencyConversionService

    code = rec.currency.code if rec.currency else base
    try:
        rate = CurrencyConversionService.strict_rate(code, base)
    except ValueError:
        return None  # no stored rate: never guess a figure
    per_month = _MONTHLY_FACTOR.get(rec.frequency, Decimal("1")) / Decimal(max(int(rec.interval or 1), 1))
    return Decimal(rec.amount) * rate * per_month


def run_recurring(user: Any, req: QueryRequest) -> QueryResult:
    from core.models import RecurringTransaction

    lang, base = req.lang, home_currency(user)
    if _not_current(req):
        return QueryResult(intro=t(lang, "only_current"))
    items = list(RecurringTransaction.objects.filter(owner=user, is_active=True).select_related("currency").order_by("next_run_date", "name"))
    if not items:
        return QueryResult(intro=t(lang, "rec_none"))
    if req.metric == "total":
        total, skipped = Decimal("0"), 0
        for rec in items:
            m = _monthly_base(rec, base)
            if m is None:
                skipped += 1
            else:
                total += m
        intro = t(lang, "rec_total", amount=money(float(total), base), n=len(items) - skipped)
        if skipped:
            intro += " " + t(lang, "rec_skipped", n=skipped)
        return QueryResult(intro=intro, facts={"monthly_total": float(total), "count": len(items) - skipped})
    today = date.today()
    if req.metric == "upcoming":
        horizon = today + timedelta(days=_UPCOMING_DAYS)
        items = [r for r in items if r.next_run_date <= horizon]
        if not items:
            return QueryResult(intro=t(lang, "rec_none_upcoming", days=_UPCOMING_DAYS))
        intro = t(lang, "rec_upcoming", n=len(items), days=_UPCOMING_DAYS)
    else:
        intro = t(lang, "rec_list", n=len(items))
    table = [Row([cell(r.name), f"{float(r.amount):,.2f} {r.currency.code if r.currency else base}",
                  t(lang, f"freq_{r.frequency}", n=int(r.interval or 1)), r.next_run_date.isoformat()]) for r in items[:MAX_ROWS]]
    return QueryResult(intro=intro, columns=[t(lang, "col_name"), t(lang, "col_amount"), t(lang, "col_frequency"), t(lang, "col_next_due")],
                       rows=table, facts={"count": len(items)})


CAPABILITIES = (
    Capability(key="budgets", provider_key="budgets", label="Budgets", terms=_BUDGET_TERMS,
               metrics=(Metric("over", (r"\bover\b|\bexceed\w*|\bovershot\b|\boverspen\w*|\bblown\b|\bnear\b|\bclose to\b|\bat risk\b|\blimit reached\b",
                                        r"تجاوز\w*|تخط\w*|زاد\w*|اقتر\w*")),
                        Metric("remaining", (r"\bleft\b|\bremain\w*|\bavailable\b|\bunspent\b", r"متبق\w*|باق\w*|فاضل\w*")),
                        Metric("status")), default_metric="status",
               filters=("category",), time="optional", follow_subject="budget", executor=run_budgets, sources=("budgets",)),
    Capability(key="recurring", provider_key="budgets", label="Recurring transactions", terms=_RECURRING_TERMS,
               metrics=(Metric("upcoming", (r"\bnext\b|\bupcoming\b|\bdue\b|\bcoming\b|\bsoon\b", r"قادم\w*|القادم\w*|مستحق\w*|الجاي\w*")),
                        Metric("total", (r"\btotal\b|\bhow much\b|\bcost\w*\b|\bcommit\w*|\bper month\b|\bmonthly total\b", r"اجمالي|كام|كم|اجمال\w*|التزام\w*")),
                        Metric("list")), default_metric="list",
               time="optional", follow_subject="recurring", executor=run_recurring, sources=("budgets",)),
)
