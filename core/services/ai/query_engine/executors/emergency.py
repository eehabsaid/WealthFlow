"""Emergency-fund capability: how many months of expenses the user's liquid money covers.

One definition, the same one the Financial Advisor screens show (portfolio optimizer `expense_baseline`):
liquid = cash + certificates (gold excluded) / average monthly expenses of the months recorded in the last
180 days. The answer states both inputs, so it can never be confused with another "average expenses" figure."""

from __future__ import annotations

import re
from typing import Any

from ..labels import t
from ..spec import Capability, Metric, QueryRequest, QueryResult
from .common import home_currency, money

DEFAULT_TARGET_MONTHS = 6
_TERMS = (
    (r"\bemergency (?:fund|funds|reserve|reserves|cash|savings)\b|\brunway\b|\bmonths? of (?:expenses|spending|living)\b|"
     r"\bhow many months\b.{0,50}\b(?:cover|last|expenses|spending)\b|\bcover\w* .{0,30}\bmonths?\b.{0,30}\b(?:expenses|spending)\b", 8),
    # Arabic is matched on NORMALISED text (hamza-on-ya folds to ya: "الطوارئ" -> "الطواري")
    (r"صندوق (?:ال)?طواري|احتياطي (?:ال)?طواري|مدخرات (?:ال)?طواري|كم شهر.{0,40}(?:مصروفات|مصاريف)|اشهر (?:من )?(?:المصروفات|المصاريف)", 8),
)
_TARGET_RE = re.compile(r"(?<!\d)(\d{1,2})\s*(?:months?|شهر|اشهر|شهور)", re.I)


def target_months(text: str) -> int:
    m = _TARGET_RE.search(text or "")
    return int(m.group(1)) if m and 1 <= int(m.group(1)) <= 60 else DEFAULT_TARGET_MONTHS


def _baseline(user: Any) -> dict[str, Any]:
    from core.services.financial_advisor.registry import get_financial_advisor_payload

    payload = get_financial_advisor_payload("portfolio_optimizer", user) or {}
    return payload.get("expense_baseline") or {}


def run(user: Any, req: QueryRequest) -> QueryResult:
    lang, home = req.lang, home_currency(user)
    base = _baseline(user)
    avg = float(base.get("avg_monthly_expenses") or 0)
    months = base.get("emergency_fund_months")
    if avg <= 0 or months is None:
        return QueryResult(intro=t(lang, "ef_no_expenses"))
    months = float(months)
    liquid = float(base.get("liquid_for_emergency") or months * avg)
    n = int(base.get("baseline_months") or 0)
    target = target_months(str(req.filters.get("target_text") or ""))
    need = avg * target
    status = t(lang, "ef_met", ratio=f"{liquid / need:,.1f}") if liquid >= need else t(lang, "ef_short", gap=money(need - liquid, home))
    intro = "\n".join([
        t(lang, "ef_head", months=f"{months:,.1f}"),
        t(lang, "ef_liquid", amount=money(liquid, home)),
        t(lang, "ef_avg", amount=money(avg, home), n=n),
        t(lang, "ef_target", target=target, amount=money(need, home), status=status),
    ])
    return QueryResult(intro=intro, facts={"months": months, "liquid": liquid, "avg_monthly_expenses": avg, "target_months": target,
                                           "currency": home})


CAPABILITIES = (Capability(
    key="emergency_fund", provider_key="financial_advisor", label="Emergency fund coverage", terms=_TERMS,
    metrics=(Metric("coverage"),), default_metric="coverage", filters=("target",), time="none",
    follow_subject="emergency fund", executor=run, sources=("financial_advisor",),
),)
