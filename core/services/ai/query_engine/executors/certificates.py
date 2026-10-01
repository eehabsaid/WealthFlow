"""Certificates capability: summary / list / next interest / nearest maturity (active certificates only)."""

from __future__ import annotations

from typing import Any

from ..labels import t
from ..spec import Capability, Metric, QueryRequest, QueryResult, Row
from .common import cell, money, provider_data

_TERMS = (
    (r"\bcertificates?\b|\bcerts?\b|\bfixed deposits?\b|\btime deposits?\b|\bdeposits?\b", 5),
    (r"شهاد(?:ه|ات)|وديع\w*|ودايع", 5),
)
_METRICS = (
    Metric("next_interest", (r"\bnext (?:interest|payout|payment|coupon)\b|\binterest (?:date|payout|payment)\b|\bwhen (?:do|will|is).{0,25}interest\b",
                              r"اقرب عايد|العايد القادم|موعد العايد|الصرف القادم|القادم")),
    Metric("maturity", (r"\b(?:matur\w*|expir\w*|due|ends?|ending)\b", r"استحقاق|تنتهي|ينتهي|انتهاء|تستحق")),
    Metric("list", (r"\b(?:list|each|all|show|details?|which)\b", r"قايمه|كل |تفاصيل|اعرض")),
    Metric("summary"),
)


def run(user: Any, req: QueryRequest) -> QueryResult:
    lang = req.lang
    data = provider_data("bank_certificates", user)
    s, items = data["summary"], data["items"]
    home = s["home_currency"]
    if not items:
        return QueryResult(intro=t(lang, "cert_none"))
    if req.metric == "next_interest":
        nxt = s.get("next_upcoming_interest")
        if not nxt:
            return QueryResult(intro=t(lang, "cert_next_none"))
        return QueryResult(intro=t(lang, "cert_next", value=nxt["next_interest_value_formatted"], bank=nxt["bank_name"], date=nxt["next_interest_date"]))
    if req.metric == "maturity":
        dated = sorted((i for i in items if i["expiry_date"]), key=lambda i: i["expiry_date"])
        if not dated:
            return QueryResult(intro=t(lang, "cert_mat_none"))
        first = dated[0]
        return QueryResult(intro=t(lang, "cert_mat", bank=first["bank_name"], amount=first["amount_formatted"], date=first["expiry_date"], days=first["days_to_maturity"]))
    if req.metric == "list":
        rows = [Row([cell(i["bank_name"]), i["amount_formatted"], i["interest_rate_formatted"], i["interest_value_monthly_formatted"], i["expiry_date"]]) for i in items]
        return QueryResult(intro=t(lang, "cert_list", n=len(items), cur=home), rows=rows,
                           columns=[t(lang, "col_bank"), t(lang, "col_principal"), t(lang, "col_rate"), t(lang, "col_interest"), t(lang, "col_expiry")])
    return QueryResult(intro=t(lang, "cert_sum", n=s["active_certificates_count"], principal=money(s["total_active_certificates_principal"], home),
                               interest=money(s["total_monthly_interest_income"], home), rate=f"{s['average_weighted_interest_rate_pct']:.2f}"),
                       facts={"principal": s["total_active_certificates_principal"], "monthly_interest": s["total_monthly_interest_income"], "currency": home})


CAPABILITIES = (Capability(
    key="certificates", provider_key="bank_certificates", label="Bank certificates & deposits", terms=_TERMS, metrics=_METRICS,
    default_metric="summary", filters=(), time="none", executor=run, sources=("bank_certificates",),
),)
