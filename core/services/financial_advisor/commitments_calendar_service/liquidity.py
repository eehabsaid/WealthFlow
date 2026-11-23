"""
Forecast-anchored liquidity analysis for the commitments calendar.

The only cash projection used is the CashFlowForecastService series (its
public payload). ForecastSeries replays that series to answer "what is the
forecast cash position at date D?". No separate projection is invented.

Analysis over the calendar events:
- projected_balance per event (forecast series value at that date)
- negative projected balance months (forecast timeline ending_cash < 0)
- concentration windows (outflow events inside a configurable N-day window)
- outflows that fall more than window_days before the next expected income
  (a long stretch with no inflow after the commitment). The risk panel always
  reflects ALL commitments in the range, independent of the display filters
- upcoming certificate maturities / asset renewals highlights
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

from core.services.financial_advisor.cash_flow_forecast_service import CashFlowForecastService

INCOME_TYPES = {"salary", "rental_income", "certificate_interest", "certificate_maturity", "asset_sale"}
RENEWAL_TYPES = {"insurance_renewal", "vehicle_license_renewal", "rental_contract_expiry"}


class ForecastSeries:
    """Running balance replayed from the forecast's own timeline events."""

    def __init__(self, owner, today: Optional[date] = None):
        payload = CashFlowForecastService(owner, today=today or date.today()).payload()
        self.as_of = payload.get("as_of")
        self.timeline = payload.get("timeline") or []
        self.events: List[dict] = []
        for month in self.timeline:
            for ev in month.get("events") or []:
                try:
                    self.events.append({
                        "date": date.fromisoformat(ev["date"]),
                        "amount": float(ev.get("amount") or 0),
                        "type": str(ev.get("type") or ""),
                    })
                except (KeyError, ValueError):
                    continue
        self.events.sort(key=lambda e: (e["date"], e["type"]))
        start = 0.0
        if self.timeline:
            first = self.timeline[0]
            start = float(first.get("ending_cash") or 0) - float(first.get("net") or 0)
        self.start_cash = round(start, 2)

    def balance_at(self, d: date) -> float:
        total = self.start_cash
        for ev in self.events:
            if ev["date"] > d:
                break
            total += ev["amount"]
        return round(total, 2)

    def next_income_after(self, d: date) -> Optional[dict]:
        for ev in self.events:
            if ev["date"] > d and ev["type"] in INCOME_TYPES:
                return ev
        return None


def _outflow_total(event: dict) -> float:
    return abs(event.get("amount_base") if event.get("amount_base") is not None else event.get("amount") or 0)


def _concentration_windows(outflows: List[dict], window_days: int) -> List[dict]:
    """Windows opening on an outflow date, ranked by total outflow.

    A window counts each commitment (same source record and event type) once,
    at its first occurrence inside the window, so one monthly bill is never
    reported as a concentration of obligations just because a short month
    puts two of its payments less than N days apart.
    """
    windows = []
    for e in outflows:
        d = date.fromisoformat(e["date"])
        end = d + timedelta(days=window_days)
        first_per_commitment = {}
        for o in outflows:
            if d <= date.fromisoformat(o["date"]) < end:
                first_per_commitment.setdefault((o["source"], o["source_id"], o["event_type"]), o)
        total = sum(_outflow_total(o) for o in first_per_commitment.values())
        windows.append({"start": d.isoformat(), "days": window_days,
                        "outflow": round(total, 2), "events": len(first_per_commitment)})
    windows.sort(key=lambda w: (-w["outflow"], w["start"]))
    deduped = []
    for w in windows:
        if not any(x["start"] == w["start"] and x["events"] == w["events"] for x in deduped):
            deduped.append(w)
    return deduped


def build_analysis(events: List[dict], window_days: int, series: ForecastSeries) -> dict:
    for e in events:
        d = date.fromisoformat(e["date"])
        e["projected_balance"] = series.balance_at(d)
        e["included_in_forecast"] = e["kind"] == "actual"

    outflows = [e for e in events if e["category"] == "expense" and e["kind"] in ("actual", "expected")]
    for e in outflows:
        d = date.fromisoformat(e["date"])
        nxt = series.next_income_after(d)
        e["days_to_next_income"] = (nxt["date"] - d).days if nxt else None
        e["before_income"] = bool(nxt and (nxt["date"] - d).days > window_days)

    negative_months = [m["month"] for m in series.timeline if float(m.get("ending_cash") or 0) < 0]

    deduped = _concentration_windows(outflows, window_days)
    concentration = [w for w in deduped if w["events"] > 1][:5]

    reasons = []
    if negative_months:
        reasons.append({"key": "commitments_risk_negative_balance", "params": {"months": len(negative_months)}})
    if concentration:
        top = concentration[0]
        reasons.append({"key": "commitments_risk_concentration",
                        "params": {"days": top["days"], "amount": top["outflow"], "events": top["events"]}})
    before = [e for e in outflows if e["before_income"]]
    if before:
        reasons.append({"key": "commitments_risk_before_income",
                        "params": {"count": len(before), "days": window_days}})

    highlights = [
        {"date": e["date"], "event_type": e["event_type"], "amount": e["amount"], "currency_code": e["currency_code"]}
        for e in events
        if e["event_type"] in RENEWAL_TYPES | {"certificate_maturity"}
    ]

    return {
        "as_of": series.as_of,
        "series_start_cash": series.start_cash,
        "negative_balance_months": negative_months,
        "concentration_windows": concentration,
        "risk_reasons": reasons,
        "highlights": highlights,
        "window_days": window_days,
    }
