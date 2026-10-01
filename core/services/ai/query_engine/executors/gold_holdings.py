"""Gold holdings capability: grams and value of the user's own gold (Balance gold entries + Fixed-asset gold).
Values come from the providers' own valuation (Balance page formula / spot karat price), owner-scoped."""

from __future__ import annotations

from typing import Any

from ..labels import t
from ..spec import Capability, Metric, QueryRequest, QueryResult, Row
from .common import cell, money, provider_data

_TERMS = (
    (r"\bhow much gold\b|\bmy gold\b|\bgold (?:holdings?|i (?:have|hold|own)|do i (?:have|hold|own)|grams?|weight|portfolio)\b|"
     r"\b(?:hold|own|have|holding)\b.{0,25}\bgold\b|\bgold\b.{0,25}\b(?:i|we) (?:hold|own|have)\b|\bgrams? of gold\b", 8),
    (r"كم (?:عندي|معي|معايا|املك|لدي)\s*(?:من )?ذهب|ذهبي|مقتنيات(?:ي)? (?:ال)?ذهب|جرامات (?:ال)?ذهب|ما املكه من ذهب|ذهب (?:عندي|معي|املكه)", 8),
)


def run(user: Any, req: QueryRequest) -> QueryResult:
    from core.models import FixedAsset

    lang = req.lang
    bal = provider_data("balance", user)
    home = bal["summary"]["home_currency"]
    rows: list[Row] = []
    grams = value = 0.0
    for i in bal["items"]:
        g = float(i.get("gold_grams") or 0)
        if g:
            v = float(i["amount_in_home_currency"])
            grams, value = grams + g, value + v
            rows.append(Row([t(lang, "src_balance") + ": " + cell(i["title"] or i["bank_name"] or "—"), str(i.get("gold_purity") or ""), f"{g:,.2f}", money(v, home)]))
    assets = provider_data("fixed_assets", user)
    by_id = {a["id"]: a for a in assets["items"]}
    for a in FixedAsset.objects.filter(owner=user, asset_type="Gold").select_related("gold_details"):
        gd = getattr(a, "gold_details", None)
        g = float(getattr(gd, "weight", 0) or 0)
        if g:
            v = float(by_id.get(a.id, {}).get("current_market_value") or 0)
            grams, value = grams + g, value + v
            rows.append(Row([t(lang, "src_asset") + ": " + cell(a.name), str(getattr(gd, "purity", "") or ""), f"{g:,.2f}", money(v, home)]))
    if not rows:
        return QueryResult(intro=t(lang, "gh_none"))
    intro = t(lang, "gh_total", grams=f"{grams:,.2f}", value=money(value, home))
    if len(rows) == 1:
        return QueryResult(intro=intro, facts={"grams": grams, "value": value, "currency": home})
    rows.append(Row([t(lang, "grand"), "", f"{grams:,.2f}", money(value, home)], bold=True))
    return QueryResult(intro=intro, rows=rows, columns=[t(lang, "col_source"), t(lang, "col_purity"), t(lang, "col_grams"), t(lang, "col_value")],
                       facts={"grams": grams, "value": value, "currency": home})


CAPABILITIES = (Capability(
    key="gold_holdings", provider_key="balance", label="Gold holdings (grams and value)", terms=_TERMS,
    metrics=(Metric("total"),), default_metric="total", filters=(), time="none", executor=run,
    sources=("balance", "fixed_assets"), follow_subject="gold",
),)
