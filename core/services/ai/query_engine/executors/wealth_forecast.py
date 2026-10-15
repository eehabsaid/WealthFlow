"""Net worth forecast capability: "how much will my wealth be on 30 Nov 2026?", "analyze my wealth".

No new maths: it reads the Financial Advisor's wealth-growth projection (the same numbers as the Wealth Growth screen:
liquid cash, certificates, gold and fixed assets per month-end, three scenarios) and shows the requested month-end
next to today's values. A date inside a month is answered with that month's end, a date beyond the model's horizon
with the last month it covers, and the answer says so. No date -> today plus the model's checkpoints."""

from __future__ import annotations

import calendar
import re
from datetime import date
from typing import Any

from ..labels import month_label, t
from ..spec import Capability, Metric, QueryRequest, QueryResult, Row
from .common import home_currency, money

_COMPONENTS = (("liquid_cash", "wf_liquid"), ("certificates", "wf_certs"), ("gold", "wf_gold"), ("fixed_assets", "wf_fixed"))
_CHECKPOINTS = (1, 3, 6, 12)
_TERMS = (
    (r"\b(?:net ?worth|wealth|total worth)\b", 6),
    (r"\bhow much (?:will|would|could) (?:i|my|it)\b.{0,50}\b(?:have|own|be worth|accumulate|save|grow)\b", 4),
    # Arabic is matched on normalised text (ta-marbuta folds to ha)
    (r"ثروت\w*|(?:ال)?ثروه|صافي (?:ال)?ثروه|صافي القيمه", 6),
)
_ANALYTIC_OK = (r"\b(?:forecast\w*|predict\w*|projections?|project|analy[sz]\w*|growth|details?|detailed)\b"
                r"|توقع\w*|حلل\w*|تحليل|بالتفصيل|تفصيل\w*")
_DAY = re.compile(r"(?<!\d)(\d{1,2})(?:st|nd|rd|th)?[\s\-/.]*(?:of\s+)?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|"
                  r"يناير|فبراير|مارس|ابريل|مايو|يونيو|يوليو|اغسطس|سبتمبر|اكتوبر|نوفمبر|ديسمبر)", re.I)


def _day_label(lang: str, d: date) -> str:
    return f"{d.day} {month_label(lang, d.year, d.month)}"


def _point(points: list[dict[str, Any]], y: int, m: int) -> int | None:
    for i, p in enumerate(points):
        if str(p.get("month_end", ""))[:7] == f"{y}-{m:02d}" and i > 0:
            return i
    return None


def _rows(lang: str, cur: str, now: dict[str, Any], cols: list[dict[str, Any]]) -> list[Row]:
    rows: list[Row] = []
    for key, label in _COMPONENTS:
        vals = [float(now.get(key) or 0), *[float(c.get(key) or 0) for c in cols]]
        if any(abs(v) > 1e-9 for v in vals):
            rows.append(Row([t(lang, label), *[money(v, cur) for v in vals]]))
    nets = [float(now.get("net_worth") or 0), *[float(c.get("net_worth") or 0) for c in cols]]
    rows.append(Row([t(lang, "wf_net"), *[money(v, cur) for v in nets]], bold=True))
    rows.append(Row([t(lang, "wf_change"), "", *[money(v - nets[0], cur) for v in nets[1:]]]))
    return rows


def run(user: Any, req: QueryRequest) -> QueryResult:
    from core.services.financial_advisor.registry import get_financial_advisor_payload

    lang, cur = req.lang, home_currency(user)
    payload = get_financial_advisor_payload("wealth_growth", user) or {}
    series = payload.get("series") or {}
    if payload.get("is_empty") or not series:
        return QueryResult(intro=t(lang, "wf_empty"))
    order = [k for k in ("conservative", "expected", "optimistic") if k in series] + [k for k in series if k not in ("conservative", "expected", "optimistic")]
    points = {k: series[k].get("points") or [] for k in order}
    base = points.get("expected") or points[order[0]]
    if len(base) < 2:
        return QueryResult(intro=t(lang, "wf_empty"))
    as_of = date.fromisoformat(str(payload.get("as_of") or date.today().isoformat())[:10])
    now = base[0]
    notes: list[str] = []
    summary = payload.get("summary") or {}

    if req.periods:
        y, m = req.periods[-1]
        day_m = _DAY.search(str(req.filters.get("target_text") or ""))
        day = int(day_m.group(1)) if day_m and 1 <= int(day_m.group(1)) <= calendar.monthrange(y, m)[1] else calendar.monthrange(y, m)[1]
        target = _day_label(lang, date(y, m, day))
        idx = _point(base, y, m)
        if (y, m) <= (as_of.year, as_of.month):
            idx = None
            notes.append(t(lang, "wf_note_past", target=target))
        elif idx is None:
            idx = len(base) - 1
            notes.append(t(lang, "wf_note_beyond", target=target, last=_day_label(lang, date.fromisoformat(str(base[idx]["month_end"])[:10]))))
        if idx is not None:
            used = date.fromisoformat(str(base[idx]["month_end"])[:10])
            if used.day != day and (y, m) == (used.year, used.month):
                notes.append(t(lang, "wf_note_month_end", target=target, used=_day_label(lang, used)))
            at = {k: (points[k][idx] if idx < len(points[k]) else base[idx]) for k in order}
            same = len({round(float(at[k].get("net_worth") or 0), 2) for k in order}) == 1
            names = [t(lang, "wf_col_forecast")] if same else [t(lang, f"wf_sc_{k}") if k in ("conservative", "expected", "optimistic") else k for k in order]
            cols = [at[order[0]]] if same else [at[k] for k in order]
            intro = t(lang, "wf_head_date", target=_day_label(lang, used), cur=cur, as_of=_day_label(lang, as_of))
            columns = [t(lang, "wf_col_item"), t(lang, "wf_col_now"), *names]
            rows = _rows(lang, cur, now, cols)
            facts = {"currency": cur, "groups": {t(lang, "wf_col_now"): float(now.get("net_worth") or 0), _day_label(lang, used): float(at["expected" if "expected" in at else order[0]].get("net_worth") or 0)}}
        else:
            intro = t(lang, "wf_head_now", cur=cur, as_of=_day_label(lang, as_of))
            columns, rows = [t(lang, "wf_col_item"), t(lang, "wf_col_now")], _rows(lang, cur, now, [])
            rows = [Row(r.cells[:2], r.bold) for r in rows[:-1]]
            facts = {"currency": cur, "total": float(now.get("net_worth") or 0)}
    else:
        idxs = [i for i in _CHECKPOINTS if i < len(base)]
        cols = [base[i] for i in idxs]
        intro = t(lang, "wf_head_now", cur=cur, as_of=_day_label(lang, as_of))
        columns = [t(lang, "wf_col_item"), t(lang, "wf_col_now"), *[str(c.get("month_end", ""))[:10] for c in cols]]
        rows = _rows(lang, cur, now, cols)
        facts = {"currency": cur, "groups": {t(lang, "wf_col_now"): float(now.get("net_worth") or 0), str(cols[-1].get("month_end", ""))[:10]: float(cols[-1].get("net_worth") or 0)}}

    monthly = float(summary.get("estimated_monthly_wealth_increase") or 0)
    if monthly:
        key = f"wf_drv_{(summary.get('largest_growth_driver') or {}).get('key') or 'none'}"
        try:
            driver = t(lang, key)
        except KeyError:
            driver = str((summary.get("largest_growth_driver") or {}).get("key") or "")
        notes.append(t(lang, "wf_monthly", amount=money(monthly, cur), driver=driver))
    return QueryResult(intro=intro, columns=columns, rows=rows, footer="\n".join(notes), facts=facts, sources=["financial_advisor"])


CAPABILITIES = (Capability(
    key="wealth_forecast", provider_key="financial_advisor", label="Net worth forecast", terms=_TERMS,
    metrics=(Metric("forecast"),), default_metric="forecast", filters=("target",), time="optional", follow_subject="net worth",
    executor=run, sources=("financial_advisor",), analytic_ok=_ANALYTIC_OK,
),)
