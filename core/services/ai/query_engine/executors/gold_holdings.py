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
    """Balance gold entries are the single source of truth: gold_sync_service mirrors every Owned gold fixed
    asset into them (same rule as net worth, which excludes Gold assets from the fixed-assets total). Adding the
    assets on top would count the same grams twice, so assets only contribute grams that are NOT in Balance."""
    from decimal import Decimal

    from core.models import FixedAsset
    from core.services.fixed_assets.gold_sync_service import _gold_weight_in_grams, _normalize_gold_purity

    lang = req.lang
    bal = provider_data("balance", user)
    home = bal["summary"]["home_currency"]
    rows: list[Row] = []
    grams = value = 0.0
    bal_by_purity: dict[str, float] = {}
    for i in bal["items"]:
        g = float(i.get("gold_grams") or 0)
        if g:
            v = float(i["amount_in_home_currency"])
            key = _normalize_gold_purity(i.get("gold_purity"))
            bal_by_purity[key] = bal_by_purity.get(key, 0.0) + g
            grams, value = grams + g, value + v
            rows.append(Row([t(lang, "src_balance") + ": " + cell(i["title"] or i["bank_name"] or "—"), str(i.get("gold_purity") or ""), f"{g:,.2f}", money(v, home)]))
    assets = FixedAsset.objects.filter(owner=user, asset_type="Gold", status="Owned").select_related("gold_details")
    asset_by_purity: dict[str, list[tuple[float, float]]] = {}   # purity -> [(grams, value)]
    for a in assets:
        gd = getattr(a, "gold_details", None)
        if gd is not None:
            g = float(_gold_weight_in_grams(gd.weight, gd.unit) or Decimal(0))
            if g:
                asset_by_purity.setdefault(_normalize_gold_purity(gd.purity), []).append((g, float(a.current_market_value or 0)))
    mirrored_n, mirrored_g = 0, 0.0
    for key, parts in asset_by_purity.items():
        total_g = sum(p[0] for p in parts)
        extra = total_g - bal_by_purity.get(key, 0.0)
        if extra > 0.005:   # grams that exist as assets but are missing from Balance (sync not run yet)
            v = sum(p[1] for p in parts) / total_g * extra
            grams, value = grams + extra, value + v
            rows.append(Row([t(lang, "src_asset"), key, f"{extra:,.2f}", money(v, home)]))
        covered = total_g - max(extra, 0.0)
        if covered > 0:
            mirrored_n += len(parts)
            mirrored_g += covered
    if not rows:
        return QueryResult(intro=t(lang, "gh_none"))
    intro = t(lang, "gh_total", grams=f"{grams:,.2f}", value=money(value, home))
    note = t(lang, "gh_synced", n=mirrored_n, grams=f"{mirrored_g:,.2f}") if mirrored_n else ""
    facts = {"grams": grams, "value": value, "currency": home}
    if len(rows) == 1:
        return QueryResult(intro=intro, footer=note, facts=facts)
    rows.append(Row([t(lang, "grand"), "", f"{grams:,.2f}", money(value, home)], bold=True))
    return QueryResult(intro=intro, rows=rows, footer=note, facts=facts,
                       columns=[t(lang, "col_source"), t(lang, "col_purity"), t(lang, "col_grams"), t(lang, "col_value")])


CAPABILITIES = (Capability(
    key="gold_holdings", provider_key="balance", label="Gold holdings (grams and value)", terms=_TERMS,
    metrics=(Metric("total"),), default_metric="total", filters=(), time="none", executor=run,
    sources=("balance", "fixed_assets"), follow_subject="gold",
),)
