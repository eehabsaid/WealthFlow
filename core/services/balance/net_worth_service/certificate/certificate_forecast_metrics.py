"""
Phase 1 of certificate_forecast_payload: pure metric computation.

NOTE (200-line file convention): see certificate_forecast_context.py for why
this is split from recommendation-building (certificate_forecast_recommendations.py)
without changing behavior. Every value a later recommendation check reads is
finalized here, in the same order as the original single-method
implementation - only the recommendation-adding calls themselves were
lifted out.
"""
from __future__ import annotations

from datetime import date, timedelta

from django.db.models import Sum

from core.models import Expense

from core.services.balance.net_worth_service.certificate.certificate_forecast_context import ForecastContext
from core.services.balance.net_worth_service.gold.certificate_forecast_gold_signal import compute_gold_signal
from core.services.balance.net_worth_service.helpers import _to_float


def build_forecast_metrics(service, today: date | None = None) -> ForecastContext:
    today = today or date.today()

    comp = service.portfolio_components()
    active_certs = service._active_certificates()
    from core.services.balance.financial_sync_service import FinancialSyncService
    rental_service = FinancialSyncService()
    monthly_rental_income = _to_float(rental_service.period_rental_income_total("month"))

    # Liquidity is calibrated from BalanceEntry cash rows only and converted to EGP via BUY rates.
    cash_balance = service._strict_liquid_assets_egp()
    certificate_balance = _to_float(comp["certificate_total_egp"])

    forecast_30 = 0.0
    forecast_90 = 0.0
    forecast_180 = 0.0
    maturing_interest_30 = 0.0
    upcoming = []

    for cert in active_certs:
        if not cert.expiry_date:
            continue

        days_left = (cert.expiry_date - today).days
        if days_left < 0:
            continue

        code = str(getattr(cert.currency, "code", "EGP") or "EGP").upper()
        amount_egp = service._converted_egp(_to_float(cert.amount), code, comp["rates"])
        interest_egp = service._converted_egp(_to_float(cert.interest_value), code, comp["rates"])

        if days_left <= 30:
            forecast_30 += amount_egp
            maturing_interest_30 += interest_egp
        if days_left <= 90:
            forecast_90 += amount_egp
        if days_left <= 180:
            forecast_180 += amount_egp

        upcoming.append(
            {
                "id": cert.id,
                "bank": cert.bank.name if cert.bank else "",
                "expiry_date": cert.expiry_date.isoformat(),
                "amount": round(amount_egp, 2),
                "interest": round(interest_egp, 2),
                "maturity_value": round(amount_egp, 2),
                "days_left": days_left,
            }
        )

    upcoming.sort(key=lambda x: x["days_left"])
    nearest_maturity = upcoming[0]["days_left"] if upcoming else None

    total_portfolio = comp["net_worth_egp"]
    if total_portfolio <= 0:
        total_portfolio = 1

    cash_ratio = (cash_balance / total_portfolio) * 100
    foreign_currency_ratio = (comp["foreign_currency_egp"] / total_portfolio) * 100
    certificate_ratio = (certificate_balance / total_portfolio) * 100
    gold_ratio = (comp["gold_value_egp"] / total_portfolio) * 100
    fixed_assets_ratio = (comp["fixed_assets_total_egp"] / total_portfolio) * 100

    last_90_days = today - timedelta(days=90)
    expenses = Expense.objects.filter(date__gte=last_90_days)
    total_expenses = _to_float(expenses.aggregate(total=Sum("amount_egp"))["total"])
    months_with_expenses = len(set(expenses.values_list("year", "month")))
    avg_monthly_expenses = total_expenses / months_with_expenses if months_with_expenses > 0 else 0
    obligations_30 = avg_monthly_expenses
    obligations_90 = avg_monthly_expenses * 3

    monthly_certificate_income = _to_float(comp["certificate_interest_total_egp"])
    from core.services.salary.salary_service import get_current_monthly_salary
    monthly_salary = get_current_monthly_salary()
    total_monthly_income = monthly_salary + monthly_certificate_income + monthly_rental_income

    cash_coverage_months = cash_balance / avg_monthly_expenses if avg_monthly_expenses > 0 else None
    certificate_income_ratio = (monthly_certificate_income / total_monthly_income) * 100 if total_monthly_income > 0 else 0

    liquidity_coverage_90 = cash_balance / obligations_90 if obligations_90 > 0 else 999.0
    maturity_support_30 = (cash_balance + forecast_30 + monthly_rental_income) / obligations_30 if obligations_30 > 0 else 999.0
    low_liquidity_flag = obligations_30 > 0 and (
        (cash_balance < obligations_90 * 0.85 and (cash_balance + forecast_30) < obligations_90)
        or (liquidity_coverage_90 < 1.1 and maturity_support_30 < 1.0)
    )

    future_cash_30 = cash_balance + forecast_30 + monthly_rental_income
    future_cash_90 = cash_balance + forecast_90 + (monthly_rental_income * 3)
    future_cash_180 = cash_balance + forecast_180 + (monthly_rental_income * 6)

    if cash_coverage_months is not None and cash_coverage_months < 3:
        low_liquidity_flag = True

    gold = compute_gold_signal(
        service,
        low_liquidity_flag=low_liquidity_flag,
        gold_ratio=gold_ratio,
        certificate_ratio=certificate_ratio,
        foreign_currency_ratio=foreign_currency_ratio,
        cash_balance=cash_balance,
        avg_monthly_expenses=avg_monthly_expenses,
    )

    return ForecastContext(
        today=today,
        comp=comp,
        cash_balance=cash_balance,
        certificate_balance=certificate_balance,
        forecast_30=forecast_30,
        forecast_90=forecast_90,
        forecast_180=forecast_180,
        maturing_interest_30=maturing_interest_30,
        upcoming=upcoming,
        nearest_maturity=nearest_maturity,
        cash_ratio=cash_ratio,
        foreign_currency_ratio=foreign_currency_ratio,
        certificate_ratio=certificate_ratio,
        gold_ratio=gold_ratio,
        fixed_assets_ratio=fixed_assets_ratio,
        avg_monthly_expenses=avg_monthly_expenses,
        monthly_certificate_income=monthly_certificate_income,
        monthly_salary=monthly_salary,
        monthly_rental_income=monthly_rental_income,
        total_monthly_income=total_monthly_income,
        cash_coverage_months=cash_coverage_months,
        certificate_income_ratio=certificate_income_ratio,
        low_liquidity_flag=low_liquidity_flag,
        future_cash_30=future_cash_30,
        future_cash_90=future_cash_90,
        future_cash_180=future_cash_180,
        gold_trend_pct=gold["gold_trend_pct"],
        gold_trend_7=gold["gold_trend_7"],
        gold_trend_30=gold["gold_trend_30"],
        gold_trend_90=gold["gold_trend_90"],
        gold_trend_365=gold["gold_trend_365"],
        gold_ma_short=gold["gold_ma_short"],
        gold_ma_long=gold["gold_ma_long"],
        gold_ma_gap_pct=gold["gold_ma_gap_pct"],
        gold_volatility=gold["gold_volatility"],
        gold_signal=gold["gold_signal"],
        neutral_band=gold["neutral_band"],
        strong_band=gold["strong_band"],
        gold_trend_state=gold["gold_trend_state"],
        gold_text=gold["gold_text"],
        gold_reason_params=gold["gold_reason_params"],
    )
