"""
Gold trend/signal/text calculation, part of the certificate forecast metrics
phase (certificate/certificate_forecast_metrics.py).

NOTE (200-line file convention): extracted from certificate_forecast_metrics.py
(which would otherwise exceed 200 lines) purely to keep build_forecast_metrics
readable. This is not a separate "phase" conceptually - it's called
synchronously from build_forecast_metrics and returns the gold-related
fields that get merged into the same ForecastContext. See
certificate/certificate_forecast_context.py for the overall phase-split
rationale.
"""
from __future__ import annotations

from typing import List, Tuple

from core.models import GoldPriceHistory

from ..helpers import _to_float


def compute_gold_signal(
    service,
    *,
    low_liquidity_flag: bool,
    gold_ratio: float,
    certificate_ratio: float,
    foreign_currency_ratio: float,
    cash_balance: float,
    avg_monthly_expenses: float,
) -> dict:
    obligations_90 = avg_monthly_expenses * 3

    gold_trend_pct = 0
    history = list(GoldPriceHistory.objects.order_by("-timestamp")[:7])
    if len(history) >= 2:
        latest_price = _to_float(history[0].carat_21k)
        avg_price = sum(_to_float(x.carat_21k) for x in history) / len(history)
        if avg_price > 0:
            gold_trend_pct = ((latest_price - avg_price) / avg_price) * 100

    gold_trend_30 = 0.0
    gold_trend_90 = 0.0
    gold_trend_365 = 0.0
    gold_trend_7 = 0.0
    gold_ma_short = 0.0
    gold_ma_long = 0.0
    gold_ma_gap_pct = 0.0
    gold_volatility = 0.0
    gold_history = list(GoldPriceHistory.objects.order_by("-timestamp")[:250])

    if len(gold_history) > 1:
        gold_trend_7 = service._gold_trend_change(gold_history, 7)
        gold_trend_30 = service._gold_trend_change(gold_history, 30)
        gold_trend_90 = service._gold_trend_change(gold_history, 90)
        gold_trend_365 = service._gold_trend_change(gold_history, 365)

        short_window = gold_history[: min(len(gold_history), 7)]
        long_window = gold_history[: min(len(gold_history), 30)]
        if short_window:
            gold_ma_short = sum(_to_float(item.carat_21k) for item in short_window) / len(short_window)
        if long_window:
            gold_ma_long = sum(_to_float(item.carat_21k) for item in long_window) / len(long_window)
        if gold_ma_long > 0:
            gold_ma_gap_pct = ((gold_ma_short - gold_ma_long) / gold_ma_long) * 100

        change_points: List[float] = []
        for idx in range(len(gold_history) - 1):
            current_price = _to_float(gold_history[idx].carat_21k)
            prev_price = _to_float(gold_history[idx + 1].carat_21k)
            if prev_price > 0:
                change_points.append(abs((current_price - prev_price) / prev_price) * 100)
            if len(change_points) >= 45:
                break
        if change_points:
            gold_volatility = sum(change_points) / len(change_points)

    trend_components: List[Tuple[float, float]] = []
    if len(gold_history) >= 5:
        trend_components.append((gold_trend_30, 0.5))
    if len(gold_history) >= 15:
        trend_components.append((gold_trend_90, 0.3))
    if len(gold_history) >= 60:
        trend_components.append((gold_trend_365, 0.2))

    if trend_components:
        total_weight = sum(weight for _, weight in trend_components)
        trend_signal = sum(value * weight for value, weight in trend_components) / total_weight if total_weight > 0 else 0.0
    else:
        trend_signal = gold_trend_pct

    allocation_liquidity_adjustment = 0.0
    if low_liquidity_flag:
        allocation_liquidity_adjustment -= 2.0
    if gold_ratio > 25:
        allocation_liquidity_adjustment -= 2.0
    if certificate_ratio > 45:
        allocation_liquidity_adjustment -= 1.0
    if foreign_currency_ratio > 35:
        allocation_liquidity_adjustment -= 0.5
    if gold_ratio < 10 and obligations_90 > 0 and cash_balance > obligations_90 * 1.25:
        allocation_liquidity_adjustment += 1.0

    trend_signal = (
        (gold_trend_7 * 0.35)
        + (gold_trend_30 * 0.40)
        + (gold_trend_90 * 0.25)
        + (gold_ma_gap_pct * 0.60)
    )

    gold_signal = trend_signal + allocation_liquidity_adjustment
    neutral_band = max(1.5, min(5.0, gold_volatility * 2.5))
    strong_band = neutral_band * 2.2

    gold_reason_params = {
        "trend_7": round(gold_trend_7, 2),
        "trend_30": round(gold_trend_30, 2),
        "trend_90": round(gold_trend_90, 2),
        "ma_short": round(gold_ma_short, 2),
        "ma_long": round(gold_ma_long, 2),
        "ma_gap": round(gold_ma_gap_pct, 2),
        "gold_ratio": round(gold_ratio, 1),
        "gold_signal": round(gold_signal, 2),
    }

    gold_trend_state = "Sideways"
    if gold_volatility >= max(2.8, neutral_band * 0.9) and abs(gold_signal) < strong_band:
        gold_trend_state = "High Volatility"
    elif gold_signal >= strong_band or (gold_trend_30 >= 8 and gold_ma_gap_pct >= 1.0):
        gold_trend_state = "Strong Uptrend"
    elif gold_signal >= neutral_band or (gold_trend_30 >= 2 and gold_ma_gap_pct > 0):
        gold_trend_state = "Moderate Uptrend"
    elif gold_signal <= -strong_band or (gold_trend_90 <= -18 and gold_ma_gap_pct < -1.0):
        gold_trend_state = "Strong Downtrend"
    elif gold_signal <= -neutral_band or (gold_trend_90 <= -12 and gold_ma_gap_pct < 0):
        gold_trend_state = "Moderate Downtrend"

    if gold_trend_90 <= -12 and gold_trend_state in {"Sideways", "Moderate Uptrend"}:
        gold_trend_state = "Moderate Downtrend"

    gold_text = (
        f"Gold trend: {gold_trend_state}. "
        f"7d {gold_trend_7:.2f}%, 30d {gold_trend_30:.2f}%, 90d {gold_trend_90:.2f}%, "
        f"MA(7) {gold_ma_short:,.2f}, MA(30) {gold_ma_long:,.2f}, gap {gold_ma_gap_pct:.2f}%."
    )
    if gold_trend_state == "Strong Uptrend":
        gold_text += (
            " Momentum is broad-based; consider a measured increase in gold allocation if liquidity remains comfortable."
        )
    elif gold_trend_state == "Moderate Uptrend":
        gold_text += " Trend is constructive; keep allocation and add gradually on pullbacks rather than in one step."
    elif gold_trend_state == "Strong Downtrend":
        gold_text += " Downtrend is pronounced; avoid aggressive additions and prioritize capital preservation."
    elif gold_trend_state == "Moderate Downtrend":
        gold_text += " Trend is soft; keep exposure controlled and use only phased entries if rebalancing is needed."
    elif gold_trend_state == "High Volatility":
        gold_text += " Price action is choppy; use smaller staged entries and avoid lump-sum timing risk."
    else:
        gold_text += " Market is range-bound; maintain strategic allocation and rebalance only if weights drift."

    if gold_ratio < 8 and not low_liquidity_flag:
        gold_text += f" Current gold weight {gold_ratio:.2f}% is low versus portfolio risk-balancing needs."
    elif gold_ratio > 28:
        gold_text += f" Current gold weight {gold_ratio:.2f}% is elevated; avoid increasing concentration."

    return {
        "gold_trend_pct": gold_trend_pct,
        "gold_trend_7": gold_trend_7,
        "gold_trend_30": gold_trend_30,
        "gold_trend_90": gold_trend_90,
        "gold_trend_365": gold_trend_365,
        "gold_ma_short": gold_ma_short,
        "gold_ma_long": gold_ma_long,
        "gold_ma_gap_pct": gold_ma_gap_pct,
        "gold_volatility": gold_volatility,
        "gold_signal": gold_signal,
        "neutral_band": neutral_band,
        "strong_band": strong_band,
        "gold_trend_state": gold_trend_state,
        "gold_text": gold_text,
        "gold_reason_params": gold_reason_params,
    }
