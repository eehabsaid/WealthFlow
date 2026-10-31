"""Categories 1 and 7 (projection) and the vague questions of 16. Net worth and its parts come from the app's wealth-growth payload (the same
figures the screen shows); the cash projection comes from the Cash Flow calculator itself (compute_custom_cash_projection, base-currency scope)."""

from __future__ import annotations

import calendar
from datetime import date

from .. import phrasing
from ..fam_util import expand, money, nonzero

PARTS = ("liquid_cash", "certificates", "gold", "fixed_assets")


def _now(user) -> dict:
    from core.services.financial_advisor.registry import get_financial_advisor_payload

    payload = get_financial_advisor_payload("wealth_growth", user) or {}
    points = ((payload.get("series") or {}).get("expected") or {}).get("points") or []
    return points[0] if points and not payload.get("is_empty") else {}


def _part_label(key: str, lang: str):
    return phrasing.concept(f"wealth_growth_component_{key}", lang)


def _projection(user):
    from core.services.financial_advisor.cash_flow_forecast_service.custom_projection import compute_custom_cash_projection

    today = date.today()
    nxt = date(today.year + (today.month == 12), today.month % 12 + 1, 1)
    target = nxt.replace(day=calendar.monthrange(nxt.year, nxt.month)[1])
    try:
        return target, compute_custom_cash_projection(user, today, target)
    except Exception:   # a forecast that cannot be computed proves nothing
        return target, None


def train(user, langs, rng) -> list:
    out, now = [], _now(user)
    if nonzero([now.get("net_worth")]):
        out += expand("networth", "networth", rng, langs, [money(now["net_worth"])], lambda l: {"x": "y"}, category="overview", level="simple")
    target, proj = _projection(user)
    if proj and nonzero([proj["projected_balance"]]):
        out += expand(f"cash_projection:{target.isoformat()}", "cash_projection", rng, langs, [money(proj["projected_balance"])],
                      lambda l: {"date": f"{target.day} {phrasing.month(l, target.year, target.month)}"}, category="cash_flow", level="complex")
    return out


def evaluate(user, langs, rng) -> list:
    out, now = [], _now(user)
    for key in PARTS:
        if nonzero([now.get(key)]):
            out += expand(f"networth_part:{key}", "networth_part", rng, langs, [money(now[key])], lambda l, k=key: {"part": _part_label(k, l)},
                          category="overview", prefix="eval:")
    _, proj = _projection(user)
    if proj and nonzero([proj["starting_balance"]]):
        out += expand("cash_now", "cash_now", rng, langs, [money(proj["starting_balance"])], lambda l: {"x": "y"}, category="cash_flow", prefix="eval:")
    return out
