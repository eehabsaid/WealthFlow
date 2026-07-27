from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

from core.models import GoldPriceHistory
from core.services.balance.net_worth_service import NetWorthService
from core.services.exchange_rate_history_service import ExchangeRateHistoryService
from core.utils import format_date


def _calc_rolling_ma(values: List[float], window: int, decimals: int = 2) -> List[float]:
    result: List[float] = []
    for i in range(len(values)):
        sub = values[max(0, i - window + 1) : i + 1]
        avg = sum(sub) / len(sub) if sub else 0.0
        result.append(round(avg, decimals))
    return result


class PerformanceService:
    def __init__(
        self,
        today: date | None = None,
        net_worth_service: NetWorthService | None = None,
        exchange_rate_history_service: ExchangeRateHistoryService | None = None,
    ):
        self.today = today or date.today()
        self._net_worth_service = net_worth_service or NetWorthService()
        self._exchange_rate_history_service = (
            exchange_rate_history_service or ExchangeRateHistoryService()
        )

    def payload(self) -> Dict[str, Any]:
        cert_forecast = self._net_worth_service.certificate_forecast_payload(today=self.today)
        balance_summary = self._net_worth_service.balance_payload().get("summary", {})

        # Gold trend %, summary moving averages, and holding value from NetWorthService
        gold_trend_7 = float(cert_forecast.get("gold_trend_7", 0.0) or 0.0)
        gold_trend_30 = float(cert_forecast.get("gold_trend_30", 0.0) or 0.0)
        gold_ma_short_summary = float(cert_forecast.get("gold_ma_short", 0.0) or 0.0)
        gold_ma_long_summary = float(cert_forecast.get("gold_ma_long", 0.0) or 0.0)
        gold_value = float(cert_forecast.get("gold_value", 0.0) or 0.0)

        # Raw Gold Price History Timeseries
        gold_history_qs = list(GoldPriceHistory.objects.order_by("timestamp"))
        gold_latest = gold_history_qs[-1] if gold_history_qs else None

        current_gold_price_24k = (
            float(gold_latest.carat_24k) if gold_latest and gold_latest.carat_24k else 0.0
        )
        latest_update_date = gold_latest.timestamp.date() if gold_latest else self.today
        latest_update_formatted = format_date(latest_update_date)

        gold_24k_values = [float(item.carat_24k) for item in gold_history_qs]
        gold_rolling_ma_short = _calc_rolling_ma(gold_24k_values, 7, decimals=2)
        gold_rolling_ma_long = _calc_rolling_ma(gold_24k_values, 30, decimals=2)

        gold_timeseries: List[Dict[str, Any]] = []
        for idx, item in enumerate(gold_history_qs):
            gold_timeseries.append(
                {
                    "timestamp": item.timestamp.isoformat(),
                    "date": format_date(item.timestamp.date()),
                    "carat_24k": float(item.carat_24k),
                    "carat_21k": float(item.carat_21k),
                    "carat_18k": float(item.carat_18k),
                    "ma_short": gold_rolling_ma_short[idx],
                    "ma_long": gold_rolling_ma_long[idx],
                }
            )

        # Exposure EGP Impact
        gold_impact_7d = gold_value * (gold_trend_7 / 100.0)
        gold_impact_30d = gold_value * (gold_trend_30 / 100.0)

        # Currency Snapshot from NetWorthService balance_payload
        usd_snapshot_rate = float(balance_summary.get("usd_rate", 0.0) or 0.0)
        eur_snapshot_rate = float(balance_summary.get("eur_rate", 0.0) or 0.0)
        sar_snapshot_rate = float(balance_summary.get("sar_rate", 0.0) or 0.0)

        currency_snapshots = {
            "USD": usd_snapshot_rate,
            "EUR": eur_snapshot_rate,
            "SAR": sar_snapshot_rate,
        }

        # Historical Exchange Rate Analytics via ExchangeRateHistoryService
        currencies = ["USD", "EUR", "SAR"]
        start_date = self.today - timedelta(days=90)
        rate_history_available = False
        currencies_data: Dict[str, Dict[str, Any]] = {}

        for code in currencies:
            current_rate = currency_snapshots.get(code, 0.0)
            qs = self._exchange_rate_history_service.get_rate_range(
                currency_code=code,
                start=start_date,
                end=self.today,
            )
            history_rows = list(qs)

            if history_rows:
                rate_history_available = True

            curr_values = [float(r.mid_rate) for r in history_rows]
            curr_rolling_ma_short = _calc_rolling_ma(curr_values, 7, decimals=4)
            curr_rolling_ma_long = _calc_rolling_ma(curr_values, 30, decimals=4)

            timeseries: List[Dict[str, Any]] = []
            for idx, row in enumerate(history_rows):
                timeseries.append(
                    {
                        "snapshot_date": row.snapshot_date.isoformat(),
                        "date": format_date(row.snapshot_date),
                        "mid_rate": float(row.mid_rate),
                        "ma_short": curr_rolling_ma_short[idx],
                        "ma_long": curr_rolling_ma_long[idx],
                    }
                )

            # Trend & Summary MA Calculations for Currency
            trend_7d = 0.0
            trend_30d = 0.0
            trend_90d = 0.0
            ma_short_summary = 0.0
            ma_long_summary = 0.0

            if history_rows:
                latest_hist_rate = float(history_rows[-1].mid_rate)
                rate_to_use = latest_hist_rate if latest_hist_rate > 0 else current_rate

                def _calc_trend(days_back: int) -> float:
                    target_d = self.today - timedelta(days=days_back)
                    past_rows = [r for r in history_rows if r.snapshot_date <= target_d]
                    if past_rows:
                        base_val = float(past_rows[-1].mid_rate)
                        if base_val > 0:
                            return ((rate_to_use - base_val) / base_val) * 100.0
                    return 0.0

                trend_7d = _calc_trend(7)
                trend_30d = _calc_trend(30)
                trend_90d = _calc_trend(90)

                ma_short_summary = curr_rolling_ma_short[-1] if curr_rolling_ma_short else rate_to_use
                ma_long_summary = curr_rolling_ma_long[-1] if curr_rolling_ma_long else rate_to_use
            else:
                rate_to_use = current_rate

            currencies_data[code] = {
                "currency_code": code,
                "current_rate": round(rate_to_use, 4),
                "trend_7d": round(trend_7d, 2),
                "trend_30d": round(trend_30d, 2),
                "trend_90d": round(trend_90d, 2),
                "ma_short": round(ma_short_summary, 4),
                "ma_long": round(ma_long_summary, 4),
                "timeseries": timeseries,
            }

        return {
            "as_of": self.today.isoformat(),
            "gold": {
                "current_price_24k": round(current_gold_price_24k, 2),
                "latest_update": latest_update_formatted,
                "trend_7d": round(gold_trend_7, 2),
                "trend_30d": round(gold_trend_30, 2),
                "ma_short": round(gold_ma_short_summary, 2),
                "ma_long": round(gold_ma_long_summary, 2),
                "timeseries": gold_timeseries,
                "exposure": {
                    "gold_value": round(gold_value, 2),
                    "impact_7d": round(gold_impact_7d, 2),
                    "impact_30d": round(gold_impact_30d, 2),
                },
            },
            "currencies": {
                "rate_history_available": rate_history_available,
                "data": currencies_data,
            },
        }
