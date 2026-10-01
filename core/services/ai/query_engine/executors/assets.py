"""Fixed-assets capability: total / by type / list / one type. Values from FixedAssetsDataProvider (gold valued at spot karat price)."""

from __future__ import annotations

from typing import Any

from ..labels import t
from ..lexicon import norm
from ..spec import Capability, Metric, QueryRequest, QueryResult, Row
from .common import cell, money, provider_data

_TERMS = (
    (r"\bfixed assets?\b|\bassets?\b|\bproperties\b|\bproperty\b|\breal estate\b|\bvillas?\b|\bapartments?\b|\bland\b|\bvehicles?\b|\bcars?\b", 3),
    (r"اصول|عقار\w*|ممتلكات\w*|شقه|شقق|فيلا|سياره|قطعه ارض", 3),
    (r"\bmy gold\b|\bgold (?:assets?|holdings?|jewel\w*|bars?|coins?)\b|ذهبي|مجوهرات", 2),
)
_METRICS = (Metric("list", (r"\b(?:list|each|all|show|details?|which)\b", r"قايمه|كل |تفاصيل|اعرض")), Metric("count", (r"\bhow many\b", r"كم عدد|عدد")), Metric("total"))
_DIMS = (("type", (r"\b(?:by|per) (?:asset )?(?:type|class|category)\b|\ballocation\b|\bbreakdown\b|\basset classes\b", r"حسب (?:ال)?نوع|توزيع|تصنيف")),)


def run(user: Any, req: QueryRequest) -> QueryResult:
    lang = req.lang
    data = provider_data("fixed_assets", user)
    s, items = data["summary"], data["items"]
    home = s["home_currency"]
    if not items:
        return QueryResult(intro=t(lang, "as_none"))
    total = float(s["total_fixed_assets_value"])
    text = str(req.filters.get("match_text") or "")
    types = [k for k in s["allocation_breakdown"] if norm(k) and norm(k) in text]
    if types and not req.group_by:
        k = types[0]
        sel = [i for i in items if i["asset_type"] == k]
        if req.metric == "list":
            items = sel
        else:
            val = float(s["allocation_breakdown"][k]["value"])
            return QueryResult(intro=t(lang, "as_type", type=k, amount=money(val, home), n=len(sel)), facts={"total": val, "currency": home})
    if req.group_by == "type":
        rows = [Row([cell(k), money(v["value"], home), v["allocation_pct_formatted"]]) for k, v in
                sorted(s["allocation_breakdown"].items(), key=lambda x: -x[1]["value"])]
        rows.append(Row([t(lang, "grand"), money(total, home), "100.0%"], bold=True))
        return QueryResult(intro=t(lang, "as_by", total=money(total, home)), rows=rows,
                           columns=[t(lang, "col_type"), t(lang, "col_value"), t(lang, "col_share")], facts={"total": total, "currency": home})
    if req.metric == "list":
        rows = [Row([cell(i["name"]), cell(i["asset_type"]), money(i["current_market_value"], home)]) for i in items]
        return QueryResult(intro=t(lang, "as_list", n=len(items), cur=home), rows=rows,
                           columns=[t(lang, "col_name"), t(lang, "col_type"), t(lang, "col_value")])
    return QueryResult(intro=t(lang, "as_total", amount=money(total, home), n=s["total_assets_count"]),
                       facts={"total": total, "count": s["total_assets_count"], "currency": home})


CAPABILITIES = (Capability(
    key="fixed_assets", provider_key="fixed_assets", label="Fixed assets", terms=_TERMS, metrics=_METRICS, default_metric="total",
    dimensions=_DIMS, filters=("asset_type",), time="none", executor=run, sources=("fixed_assets",),
),)
