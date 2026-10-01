"""Balance capability: total / by currency | account type | account, currency and bank filters.
Numbers come from BalanceDataProvider (same gold valuation + home-currency conversion as the Balance page)."""

from __future__ import annotations

from typing import Any

from ..labels import t
from ..lexicon import norm
from ..spec import Capability, Metric, QueryRequest, QueryResult, Row
from .common import cell, money, provider_data

_TERMS = (
    (r"\bbalances?\b|\bliquid\b|\bbank accounts?\b|\baccounts?\b|\bcash on hand\b|\bfunds\b|\bwallet\b|"
     r"\bmoney (?:do i have|i have|i hold|do i hold)\b|\bhow much (?:money|cash)\b|\bhow much do i have\b", 3),
    (r"\bhow much \w+ do i (?:have|hold)\b|\bin the bank\b|في البنك", 3),
    (r"رصيد\w*|ارصده|حساب\w*|فلوس\w*|كاش|سيوله|اموالي|كم معي|معايا كام", 3),
    (r"\bsavings?\b|\bcash\b|مدخرات\w*", 2),
)
_METRICS = (Metric("list", (r"\b(?:list|each|all|show|details?|which)\b", r"قايمه|كل|تفاصيل|اعرض")), Metric("total"))
_DIMS = (
    ("currency", (r"\b(?:by|per|each) currenc\w*|\bcurrencies\b", r"حسب (?:ال)?عمل\w*|لكل عمله|العملات")),
    ("type", (r"\b(?:by|per) (?:account )?type\b|\bcash vs\b|\baccount types?\b", r"حسب (?:ال)?نوع|انواع الحسابات")),
    ("account", (r"\b(?:by|per) (?:bank|account)\b(?! type)|\beach (?:bank|account)\b|\bbanks\b|\ball (?:my )?accounts\b|\baccounts list\b",
                 r"حسب (?:ال)?(?:بنك|حساب)|لكل (?:بنك|حساب)|البنوك|كل الحسابات")),
)


def _sum(items: list[dict], key: str) -> float:
    return sum(float(i.get(key) or 0) for i in items)


def run(user: Any, req: QueryRequest) -> QueryResult:
    lang = req.lang
    data = provider_data("balance", user)
    items, s = data["items"], data["summary"]
    home = s["home_currency"]
    if not items:
        return QueryResult(intro=t(lang, "bal_none"))
    codes = req.filters.get("currencies") or []
    text = str(req.filters.get("match_text") or "")
    banks = [b for b in {i["bank_name"] for i in items if i["bank_name"]} if norm(b) and norm(b) in text]
    if banks:
        sel = [i for i in items if i["bank_name"] in banks]
        return QueryResult(intro=t(lang, "bal_bank", bank=", ".join(banks), home=money(_sum(sel, "amount_in_home_currency"), home), n=len(sel)),
                           facts={"total": _sum(sel, "amount_in_home_currency"), "currency": home})
    if codes and not req.group_by:
        lines = []
        for c in codes:
            sel = [i for i in items if str(i["currency"]).upper() == c]
            lines.append(t(lang, "bal_cur", cur=c, amount=money(_sum(sel, "amount"), c), n=len(sel), home=money(_sum(sel, "amount_in_home_currency"), home))
                         if sel else t(lang, "bal_cur_none", cur=c))
        return QueryResult(intro="\n".join(lines))
    group = req.group_by or ("account" if req.metric == "list" else "")
    total = float(s["total_liquid_in_home_currency"])
    if not group:
        intro = t(lang, "bal_total", amount=money(total, home), n=s["total_accounts_count"])
        if s.get("gold_grams_total"):
            intro += " " + t(lang, "bal_gold_note", amount=money(s["gold_value_in_home_currency"], home))
        return QueryResult(intro=intro, facts={"total": total, "currency": home, "accounts": s["total_accounts_count"]})
    hdr_home = t(lang, "col_home", cur=home)
    if group == "account":
        rows = [Row([cell(i["title"] or i["bank_name"] or "—"), cell(i["bank_name"]), str(i["balance_type"] or ""), money(i["amount"], i["currency"]),
                     money(i["amount_in_home_currency"], home)]) for i in items]
        cols = [t(lang, "col_account"), t(lang, "col_bank"), t(lang, "col_type"), t(lang, "col_balance"), hdr_home]
    else:
        key, col = ("currency", t(lang, "col_currency")) if group == "currency" else ("balance_type", t(lang, "col_type"))
        buckets: dict[str, list[dict]] = {}
        for i in items:
            buckets.setdefault(str(i[key] or "—"), []).append(i)
        rows = [Row([k, money(_sum(v, "amount"), k) if key == "currency" else "", money(_sum(v, "amount_in_home_currency"), home)])
                for k, v in sorted(buckets.items(), key=lambda x: -_sum(x[1], "amount_in_home_currency"))]
        cols = [col, t(lang, "col_balance"), hdr_home]
    rows.append(Row([t(lang, "grand"), *[""] * (len(cols) - 2), money(total, home)], bold=True))
    return QueryResult(intro=t(lang, "bal_by", dim=t(lang, f"dim_{group}"), total=money(total, home)), columns=cols, rows=rows,
                       facts={"total": total, "currency": home})


CAPABILITIES = (Capability(
    key="balance", provider_key="balance", label="Bank & liquid balances", terms=_TERMS, metrics=_METRICS, default_metric="total",
    dimensions=_DIMS, filters=("currency", "bank"), time="none", follow_subject="balance", executor=run, sources=("balance",),
),)
