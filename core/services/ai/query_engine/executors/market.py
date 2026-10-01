"""Market-data capabilities: gold price by karat (buy/sell) and exchange rates.

GoldPrice / ExchangeRate have no owner column: market data is global, so there is no owner filter
(and nothing here reads any per-user table). Gold prices are quoted in GOLD_PRICE_CURRENCY; exchange
rates are expressed against the user's home currency exactly like CurrencyConversionService (buy leg).
"""

from __future__ import annotations

from typing import Any

from ..labels import t
from ..spec import Capability, Metric, QueryRequest, QueryResult, Row
from .common import home_currency

_KARATS = ("24", "22", "21", "18")
_FIELDS = {"24": "carat_24k", "22": "carat_22k", "21": "carat_21k", "18": "carat_18k"}
_GOLD_TERMS = (
    (r"\bgold\b.{0,40}\b(?:price|prices|rate|rates|cost|worth|value|quote)\b|\b(?:price|prices|rate|rates|cost|value)\b.{0,15}\bgold\b|"
     r"\bgold\b.{0,15}\bper gram\b|\b(?:24|22|21|18)\s?-?\s?k(?:t|arat)?\b|\bkarat\b|\bcarat\b|\bgold ounce\b|\bounce\b", 5),
    (r"سعر\s+(?:ال)?ذهب|ذهب.{0,20}سعر|سعر جرام|عيار\s*\d+|اسعار الذهب|جرام الذهب|جنيه ذهب|اونصه|اوقيه", 5),
    (r"\bgold\b|ذهب", 1),
)
_FX_CODES = r"(?:usd|eur|gbp|sar|aed|kwd|qar|dollars?|euros?|pounds?|riyals?|dirhams?|dinars?)"
_FX_TERMS = (
    (rf"\bexchange rates?\b|\bfx\b|\bforex\b|\bconversion rate\b|\bcurrency (?:rates?|prices?)\b|\b{_FX_CODES}\b.{{0,14}}\b(?:rate|price)\b|"
     rf"\b(?:rate|price)\b.{{0,14}}\b{_FX_CODES}\b|\bhow much is (?:the )?(?:1 |one )?{_FX_CODES}\b|\b(?:usd|eur|gbp|sar|aed|kwd)\s*(?:to|/)\s*\w{{3}}\b", 5),
    (r"سعر\s+(?:ال)?(?:دولار|يورو|ريال|درهم|دينار|جنيه استرليني)|سعر الصرف|اسعار الصرف|اسعار العملات|سعر العمله|كام الدولار|بكام الدولار|الدولار بكام|الدولار النهارده|الدولار النهاردة", 5),
    (rf"\b{_FX_CODES}\b|دولار|يورو|ريال|درهم", 1),
)


def _when(dt: Any) -> str:
    from django.utils import timezone

    return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M") if dt else "—"


def _num(x: Any) -> str:
    v = float(x or 0)
    return f"{v:,.2f}" if v > 0 else "—"


def run_gold(user: Any, req: QueryRequest) -> QueryResult:
    from core.models import GoldPrice
    from core.services.shared.base_currency import GOLD_PRICE_CURRENCY

    lang = req.lang
    g = GoldPrice.objects.order_by("-fetched_at", "-id").first()
    if g is None:
        return QueryResult(intro=t(lang, "gold_none"))
    when, cur = _when(g.fetched_at), GOLD_PRICE_CURRENCY
    if req.metric == "ounce":
        return QueryResult(intro=t(lang, "gold_oz", usd=_num(g.usd_per_oz), usd_g=_num(g.usd_gram_24k), when=when),
                           facts={"usd_per_oz": float(g.usd_per_oz)})
    k = str(req.filters.get("karat") or "")
    side = str(req.filters.get("side") or "")
    if k and k not in _KARATS:
        return QueryResult(intro=t(lang, "gold_bad_karat"))
    if not k:
        rows = [Row([f"{x}K", _num(getattr(g, _FIELDS[x])), _num(getattr(g, _FIELDS[x] + "_buy"))]) for x in _KARATS]
        return QueryResult(intro=t(lang, "gold_all", cur=cur, when=when), rows=rows,
                           columns=[t(lang, "col_karat"), t(lang, "col_sell"), t(lang, "col_buy")],
                           facts={f"{x}k_sell": float(getattr(g, _FIELDS[x])) for x in _KARATS})
    sell, buy = getattr(g, _FIELDS[k]), getattr(g, _FIELDS[k] + "_buy")
    if side in ("buy", "sell"):
        price = f"{_num(buy if side == 'buy' else sell)} {cur}"
        return QueryResult(intro=t(lang, "gold_side", k=k, side=t(lang, f"side_{side}"), price=price, when=when), facts={"price": float(buy if side == 'buy' else sell)})
    return QueryResult(intro=t(lang, "gold_one", k=k, sell=f"{_num(sell)} {cur}", buy=f"{_num(buy)} {cur}", when=when), facts={"sell": float(sell), "buy": float(buy)})


def _latest_rows() -> dict[str, Any]:
    from django.db.models import Max

    from core.models import ExchangeRate

    ids = ExchangeRate.objects.values("currency_code").annotate(m=Max("id")).values_list("m", flat=True)
    return {r.currency_code.upper(): r for r in ExchangeRate.objects.filter(id__in=ids)}


def run_fx(user: Any, req: QueryRequest) -> QueryResult:
    from core.services.shared.currency_conversion_service import CurrencyConversionService

    lang, home = req.lang, home_currency(user)
    rates = _latest_rows()
    if not rates:
        return QueryResult(intro=t(lang, "fx_empty"))
    denom = float(CurrencyConversionService.get_latest_buy_rate(home)) or 1.0  # home leg (1.0 when home is the pivot)
    side = str(req.filters.get("side") or "")
    codes = [c for c in (req.filters.get("currencies") or []) if c != home]
    latest = max(r.fetched_at for r in rates.values())

    def val(r, leg):
        return float(getattr(r, leg) or 0) / denom

    if not codes:
        rows = [Row([c, f"{val(r, 'buy_rate'):,.4f}", f"{val(r, 'sell_rate'):,.4f}", f"{val(r, 'mid_rate'):,.4f}"]) for c, r in sorted(rates.items()) if c != home][:40]
        return QueryResult(intro=t(lang, "fx_all", home=home, when=_when(latest)), rows=rows,
                           columns=[t(lang, "col_currency"), t(lang, "col_buy"), t(lang, "col_sell"), t(lang, "col_mid")])
    lines, facts = [], {}
    for c in codes:
        r = rates.get(c)
        if r is None:
            lines.append(t(lang, "fx_none", code=c))
            continue
        facts[c] = val(r, "buy_rate")
        if side in ("buy", "sell", "mid"):
            leg = {"buy": "buy_rate", "sell": "sell_rate", "mid": "mid_rate"}[side]
            lines.append(t(lang, "fx_side", code=c, price=f"{val(r, leg):,.4f}", home=home, side=t(lang, f"side_{side}"), when=_when(r.fetched_at)))
        else:
            lines.append(t(lang, "fx_one", code=c, mid=f"{val(r, 'mid_rate'):,.4f}", home=home, buy=f"{val(r, 'buy_rate'):,.4f}",
                           sell=f"{val(r, 'sell_rate'):,.4f}", when=_when(r.fetched_at)))
    return QueryResult(intro="\n".join(lines), facts=facts)


CAPABILITIES = (
    Capability(key="gold_price", provider_key="market_data", label="Gold price by karat", terms=_GOLD_TERMS,
               metrics=(Metric("ounce", (r"\bounce\b|\boz\b", r"اونصه|اوقيه")), Metric("price")), default_metric="price",
               filters=("karat", "side"), time="none", executor=run_gold, sources=("market_data",)),
    Capability(key="exchange_rates", provider_key="market_data", label="Exchange rates", terms=_FX_TERMS,
               metrics=(Metric("rate"),), default_metric="rate", filters=("currency", "side"), time="none", executor=run_fx, sources=("market_data",)),
)
