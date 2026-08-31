"""
NOTE: Part of the cash_flow_forecast_service package split (see helpers.py
docstring for the 200-line-per-file convention this package follows).

TimelineMixin: turns the flat ForecastEvent list into day-based
checkpoints, a month-grouped timeline, a flattened timeline-events list,
and month-based checkpoints. Composed onto CashFlowForecastService in
core.py.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List

from .helpers import ForecastEvent, to_float


class TimelineMixin:
    def _checkpoints(self, initial_cash: float, events: List[ForecastEvent]) -> Dict[int, float]:
        checkpoint_dates = {days: self.today + timedelta(days=days) for days in self.CHECKPOINT_DAYS}
        result: Dict[int, float] = {}

        running_cash = initial_cash
        idx = 0
        for days in sorted(checkpoint_dates.keys()):
            target = checkpoint_dates[days]
            while idx < len(events) and events[idx].event_date <= target:
                running_cash += events[idx].amount_egp
                idx += 1
            result[days] = running_cash
        return result

    def _timeline(self, initial_cash: float, events: List[ForecastEvent]) -> List[dict]:
        grouped: Dict[str, dict] = {}
        for month_end in self._month_end_dates():
            month_key = f"{month_end.year:04d}-{month_end.month:02d}"
            grouped[month_key] = {
                "month": month_key,
                "events": [],
                "inflow": 0.0,
                "outflow": 0.0,
                "net": 0.0,
                "ending_cash": 0.0,
            }

        monthly_interest_sum: Dict[str, float] = {}
        monthly_interest_date: Dict[str, date] = {}

        for event in events:
            month_key = f"{event.event_date.year:04d}-{event.event_date.month:02d}"
            if month_key not in grouped:
                grouped[month_key] = {
                    "month": month_key,
                    "events": [],
                    "inflow": 0.0,
                    "outflow": 0.0,
                    "net": 0.0,
                    "ending_cash": 0.0,
                }

            item = grouped[month_key]
            if event.event_type == "certificate_interest":
                monthly_interest_sum[month_key] = monthly_interest_sum.get(month_key, 0.0) + event.amount_egp
                prev_date = monthly_interest_date.get(month_key)
                monthly_interest_date[month_key] = max(prev_date, event.event_date) if prev_date else event.event_date
                continue

            event_payload = {
                "date": event.event_date.isoformat(),
                "type": event.event_type,
                "amount": round(event.amount_egp, 2),
            }
            item["events"].append(event_payload)

        for month_key, amount in monthly_interest_sum.items():
            item = grouped[month_key]
            event_payload = {
                "date": (monthly_interest_date.get(month_key) or date.fromisoformat(f"{month_key}-01")).isoformat(),
                "type": "certificate_interest",
                "amount": round(amount, 2),
            }
            item["events"].append(event_payload)

        timeline = []
        running_cash = initial_cash
        for month_key in sorted(grouped.keys()):
            month_item = grouped[month_key]
            month_item["events"].sort(key=lambda e: (e["date"], e["type"]))

            month_inflow = 0.0
            month_outflow = 0.0
            month_net = 0.0
            for event in month_item["events"]:
                amount = to_float(event.get("amount"))
                if amount >= 0:
                    month_inflow += amount
                else:
                    month_outflow += abs(amount)
                month_net += amount

            running_cash += month_net
            month_item["inflow"] = round(month_inflow, 2)
            month_item["outflow"] = round(month_outflow, 2)
            month_item["net"] = round(month_net, 2)
            month_item["ending_cash"] = round(running_cash, 2)
            timeline.append(month_item)

        return timeline

    def _timeline_events(self, timeline: List[dict]) -> List[dict]:
        out: List[dict] = []
        for month in timeline:
            month_events = month.get("events") or []
            for event in month_events:
                out.append(
                    {
                        "date": str(event.get("date") or ""),
                        "type": str(event.get("type") or "none"),
                        "amount": to_float(event.get("amount")),
                    }
                )
        out.sort(key=lambda item: (item["date"], item["type"]))
        return out

    def _month_based_checkpoints(self, current_cash: float, timeline: List[dict]) -> Dict[str, float]:
        def _ending_cash_at(month_offset: int) -> float:
            if not timeline:
                return current_cash

            index = min(max(month_offset, 0), len(timeline) - 1)
            return to_float(timeline[index].get("ending_cash"))

        return {
            "current": round(current_cash, 2),
            "next_month": round(_ending_cash_at(1), 2),
            "month_3": round(_ending_cash_at(3), 2),
            "month_6": round(_ending_cash_at(6), 2),
            "month_12": round(_ending_cash_at(12), 2),
        }
