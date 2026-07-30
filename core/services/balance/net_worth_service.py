from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Dict, List, Tuple, TypeVar, cast

from django.db.models import Sum, Q

from core.models import (
    AppSettings,
    BalanceEntry,
    Currency,
    AssetMortgage,
    AssetRental,
    BankCertificate,
    ExchangeRate,
    Expense,
    FixedAsset,
    GoldPrice,
    GoldPriceHistory,
    GoldPuritySetting,
    _is_certificate_active,
)
from core.services.balance.financial_sync_service import FinancialSyncService

REAL_ESTATE_ASSET_TYPES = {"Real Estate"}
VEHICLE_ASSET_TYPES = {"Vehicles"}
OTHER_ASSET_TYPES = {"Other Assets"}
T = TypeVar("T")

def _to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0

def _to_decimal(value, default="0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)

def _normalize_gold_purity(purity_value) -> str:
    text = str(purity_value or "").strip().lower()
    if "24" in text or "999" in text:
        return "24k"
    if "22" in text or "916" in text:
        return "22k"
    if "21" in text or "875" in text:
        return "21k"
    if "18" in text or "750" in text:
        return "18k"
    return "24k"

class NetWorthService:
    _shared_cache: Dict[str, Any] = {}
    _shared_cache_time: float = 0.0

    def __init__(self, cache: Dict[str, Any] | None = None):
        self._cache = cache if cache is not None else {}

    def _cached(self, key: str, producer: Callable[[], T]) -> T:
        if key not in self._cache:
            self._cache[key] = producer()
        return cast(T, self._cache[key])

    def _latest_rates(self) -> Dict[str, float]:
        def _load():
            rates: Dict[str, float] = {}
            for rate in ExchangeRate.objects.order_by("currency_code", "-fetched_at"):
                code = str(rate.currency_code or "").upper()
                if code and code not in rates:
                    rates[code] = _to_float(rate.buy_rate)
            return rates

        return self._cached("latest_rates", _load)

    def _latest_gold_price(self):
        return self._cached("latest_gold", lambda: GoldPrice.objects.order_by("-fetched_at").first())

    def _gold_cashback_by_key(self) -> Dict[str, float]:
        def _load():
            return {
                str(setting.key or "").lower(): _to_float(setting.cashback_per_gram)
                for setting in GoldPuritySetting.objects.filter(is_active=True)
            }

        return self._cached("gold_cashback", _load)

    def _sell_price_per_gram(self, purity_key: str) -> float:
        latest_gold = self._latest_gold_price()
        if not latest_gold:
            return 0.0

        if purity_key == "22k":
            return _to_float(latest_gold.carat_22k)
        if purity_key == "21k":
            return _to_float(latest_gold.carat_21k)
        if purity_key == "18k":
            return _to_float(latest_gold.carat_18k)
        return _to_float(latest_gold.carat_24k)

    def _active_certificates(self) -> List[BankCertificate]:
        def _load():
            certs = BankCertificate.objects.select_related("bank", "currency").all()
            return [c for c in certs if _is_certificate_active(c)]

        return self._cached("active_certs", _load)

    def _certificate_projection_map(self) -> Dict[Tuple[int, int], float]:
        def _load():
            grouped: Dict[Tuple[int, int], float] = {}
            for cert in self._active_certificates():
                key = (cert.bank_id or 0, cert.currency_id or 0)
                grouped[key] = grouped.get(key, 0.0) + _to_float(cert.amount)
            return grouped

        return self._cached("cert_projection", _load)

    def _converted_egp(self, amount: float, currency_code: str, rates: Dict[str, float]) -> float:
        from core.services.balance.net_worth_calculations import converted_egp
        return converted_egp(amount, currency_code, rates)

    def _projected_balance_entries(self) -> List[dict]:
        def _load():
            entries = list(BalanceEntry.objects.select_related("bank", "currency").all())
            cert_map = self._certificate_projection_map()
            egp_currency = Currency.objects.filter(code__iexact="EGP").first()
            virtual_entries: List[dict] = []

            def _virtual_entry(title: str, amount: float, source_key: str) -> dict:
                currency = egp_currency
                return {
                    "id": f"virtual-{source_key}",
                    "title": title,
                    "balance_type": BalanceEntry.BalanceType.CASH,
                    "bank_id": None,
                    "bank_name": "",
                    "currency_id": currency.id if currency else None,
                    "currency_code": currency.code if currency else "EGP",
                    "currency_symbol": currency.symbol if currency else "",
                    "currency_flag": currency.flag if currency else "💱",
                    "currency_name": currency.name if currency else "Egyptian Pound",
                    "purity": "",
                    "amount": round(amount, 2),
                    "notes": "",
                }

            rental_qs = (
                AssetRental.objects.select_related("asset")
                .filter(asset__asset_type__in=REAL_ESTATE_ASSET_TYPES, asset__status="Owned")
                .order_by("id")
            )
            for rental in rental_qs:
                monthly_rent = _to_float(rental.monthly_rent)
                occupancy_rate = _to_float(rental.occupancy_rate)
                rental_income = monthly_rent * occupancy_rate / 100.0
                if rental_income <= 0:
                    continue
                virtual_entries.append(
                    _virtual_entry(
                        f"{rental.asset.name} Rental Income",
                        rental_income,
                        f"rental-income-{rental.id}",
                    )
                )

            mortgage_qs = (
                AssetMortgage.objects.select_related("asset")
                .filter(asset__asset_type__in=REAL_ESTATE_ASSET_TYPES, asset__status="Owned")
                .order_by("id")
            )
            for mortgage in mortgage_qs:
                remaining_balance = _to_float(mortgage.remaining_balance)
                if remaining_balance <= 0:
                    continue
                virtual_entries.append(
                    _virtual_entry(
                        f"{mortgage.asset.name} Mortgage Liability",
                        -remaining_balance,
                        f"mortgage-liability-{mortgage.id}",
                    )
                )

            payload = []
            for entry in entries:
                if entry.balance_type == BalanceEntry.BalanceType.CERTIFICATE:
                    key = (entry.bank_id or 0, entry.currency_id or 0)
                    active_total = cert_map.get(key, 0.0)
                    if active_total <= 0:
                        continue
                    item = entry.to_dict()
                    item["amount"] = active_total
                    payload.append(item)
                else:
                    payload.append(entry.to_dict())
            payload.extend(virtual_entries)
            return payload

        return self._cached("projected_entries", _load)

    def _fixed_assets_breakdown(self) -> Dict[str, float]:
        def _load():
            owned = FixedAsset.objects.filter(status="Owned")
            agg = owned.aggregate(
                real_estate=Sum("current_market_value", filter=Q(asset_type__in=REAL_ESTATE_ASSET_TYPES)),
                vehicles=Sum("current_market_value", filter=Q(asset_type__in=VEHICLE_ASSET_TYPES)),
                other_assets=Sum("current_market_value", filter=Q(asset_type__in=OTHER_ASSET_TYPES)),
            )
            return {
                "real_estate": _to_float(agg.get("real_estate")),
                "vehicles": _to_float(agg.get("vehicles")),
                "other_assets": _to_float(agg.get("other_assets")),
            }

        return self._cached("fixed_assets_breakdown", _load)

    def _strict_liquid_assets_egp(self) -> float:
        """
        Liquidity definition for recommendation calibration:
        - Source: BalanceEntry only
        - Filter: balance_type = Cash and currency != Gold (case-insensitive)
        - Conversion: latest BUY rate only for non-EGP rows
        """
        rates = self._latest_rates()
        total = 0.0

        rows = (
            BalanceEntry.objects.select_related("currency")
            .filter(balance_type__iexact=BalanceEntry.BalanceType.CASH)
            .exclude(currency__code__iexact="GOLD")
        )

        for row in rows:
            code = str(getattr(row.currency, "code", "") or "").upper()
            amount = _to_float(row.amount)
            if code == "EGP":
                total += amount
            elif code:
                total += amount * _to_float(rates.get(code))

        return total

    def _strict_egp_cash_balance(self) -> float:
        """
        Strict EGP cash for Financial Intelligence card:
        - Source: BalanceEntry only
        - Filter: balance_type = cash AND currency = EGP (case-insensitive)
        - Includes both bank and non-bank rows
        """
        agg = (
            BalanceEntry.objects.filter(
                balance_type__iexact=BalanceEntry.BalanceType.CASH,
                currency__code__iexact="EGP",
            ).aggregate(total=Sum("amount"))
        )
        return _to_float(agg.get("total"))

    def _gold_trend_change(self, history: List[GoldPriceHistory], window_days: int) -> float:
        from core.services.balance.net_worth_calculations import gold_trend_change
        return gold_trend_change(history, window_days)

    def _append_unique(self, items: List[str], value: str) -> None:
        from core.services.balance.net_worth_calculations import append_unique
        append_unique(items, value)

    def portfolio_components(self) -> dict:
        def _build():
            rates = self._latest_rates()
            entries = self._projected_balance_entries()
            totals_by_currency: Dict[str, float] = {}

            cash_total = 0.0
            banks_total = 0.0
            cash_egp_legacy = 0.0
            cert_legacy_egp = 0.0
            foreign_value = 0.0
            gold_value = 0.0
            gold_grams = 0.0

            cashback_map = self._gold_cashback_by_key()

            for item in entries:
                code = str(item.get("currency_code") or "").upper()
                amount = _to_float(item.get("amount"))
                balance_type = str(item.get("balance_type") or "")
                totals_by_currency[code] = totals_by_currency.get(code, 0.0) + amount

                if balance_type == BalanceEntry.BalanceType.CERTIFICATE:
                    if code == "EGP":
                        cert_legacy_egp += amount
                    continue

                if code == "GOLD":
                    purity_key = _normalize_gold_purity(item.get("purity"))
                    sell_price = self._sell_price_per_gram(purity_key)
                    cashback = _to_float(cashback_map.get(purity_key, 0.0))
                    gold_grams += amount
                    gold_value += amount * (sell_price + cashback)
                    continue

                converted = self._converted_egp(amount, code, rates)
                if code != "EGP":
                    foreign_value += converted
                else:
                    cash_egp_legacy += amount

                if balance_type == BalanceEntry.BalanceType.BANK:
                    banks_total += converted
                else:
                    cash_total += converted

            cert_total_egp = 0.0
            cert_interest_total_egp = 0.0
            for cert in self._active_certificates():
                code = str(getattr(cert.currency, "code", "EGP") or "EGP").upper()
                cert_total_egp += self._converted_egp(_to_float(cert.amount), code, rates)
                cert_interest_total_egp += self._converted_egp(_to_float(cert.interest_value), code, rates)

            fixed_breakdown = self._fixed_assets_breakdown()
            fixed_total = fixed_breakdown["real_estate"] + fixed_breakdown["vehicles"] + fixed_breakdown["other_assets"]
            liquid_total = cash_total + banks_total + cert_total_egp + gold_value
            net_worth = liquid_total + fixed_total

            allocation_values = {
                "type_cash": cash_total + banks_total,
                "bank_certificates": cert_total_egp,
                "type_gold": gold_value,
                "type_real_estate": fixed_breakdown["real_estate"],
                "type_vehicles": fixed_breakdown["vehicles"],
                "type_other_assets": fixed_breakdown["other_assets"],
            }
            allocation_pct = {
                key: round((value / net_worth) * 100, 2) if net_worth > 0 else 0.0
                for key, value in allocation_values.items()
            }

            return {
                "entries": entries,
                "totals_by_currency": totals_by_currency,
                "rates": rates,
                "cash_egp_legacy": cash_egp_legacy - cert_legacy_egp,
                "certificate_egp_legacy": cert_legacy_egp,
                "cash_total_egp": cash_total,
                "banks_total_egp": banks_total,
                "foreign_currency_egp": foreign_value,
                "certificate_total_egp": cert_total_egp,
                "certificate_interest_total_egp": cert_interest_total_egp,
                "gold_value_egp": gold_value,
                "gold_grams": gold_grams,
                "fixed_assets": fixed_breakdown,
                "fixed_assets_total_egp": fixed_total,
                "liquid_assets_total_egp": liquid_total,
                "net_worth_egp": net_worth,
                "allocation_values": allocation_values,
                "allocation_percentages": allocation_pct,
            }

        return self._cached("portfolio_components", _build)

    def balance_payload(self) -> dict:
        comp = self.portfolio_components()
        rates = comp["rates"]
        totals_by_currency = comp["totals_by_currency"]
        liquid_egp_cash = self._strict_egp_cash_balance()

        usd_amount = _to_float(totals_by_currency.get("USD"))
        eur_amount = _to_float(totals_by_currency.get("EUR"))
        sar_amount = _to_float(totals_by_currency.get("SAR"))

        usd_rate = _to_float(rates.get("USD"))
        eur_rate = _to_float(rates.get("EUR"))
        sar_rate = _to_float(rates.get("SAR"))

        egp_amount = _to_float(totals_by_currency.get("EGP"))
        usd_value = usd_amount * usd_rate
        eur_value = eur_amount * eur_rate
        sar_value = sar_amount * sar_rate
        balance_only_grand_total = (
            egp_amount
            + usd_value
            + eur_value
            + sar_value
            + _to_float(comp["gold_value_egp"])
        )

        return {
            "entries": comp["entries"],
            "summary": {
                "totals_by_currency": totals_by_currency,
                "cash_egp": round(comp["cash_egp_legacy"], 2),
                "liquid_egp_cash": round(liquid_egp_cash, 2),
                "certificate_egp": round(comp["certificate_egp_legacy"], 2),
                "usd_rate": usd_rate,
                "eur_rate": eur_rate,
                "sar_rate": sar_rate,
                "usd_value": round(usd_value, 2),
                "eur_value": round(eur_value, 2),
                "sar_value": round(sar_value, 2),
                "gold_value": round(comp["gold_value_egp"], 2),
                "liquid_total": round(comp["liquid_assets_total_egp"], 2),
                "fixed_assets_total": round(comp["fixed_assets_total_egp"], 2),
                "real_estate_value": round(comp["fixed_assets"]["real_estate"], 2),
                "vehicles_value": round(comp["fixed_assets"]["vehicles"], 2),
                "other_assets_value": round(comp["fixed_assets"]["other_assets"], 2),
                "net_worth": round(comp["net_worth_egp"], 2),
                "grand_total": round(balance_only_grand_total, 2),
                "allocation_values": comp["allocation_values"],
                "allocation_percentages": comp["allocation_percentages"],
            },
        }

    def fixed_assets_snapshot(self) -> dict:
        comp = self.portfolio_components()
        net_worth = comp["net_worth_egp"]
        fixed_total = comp["fixed_assets_total_egp"]
        liquid_total = comp["liquid_assets_total_egp"]

        fixed_ratio = (fixed_total / net_worth) * 100 if net_worth > 0 else 0
        liquid_ratio = (liquid_total / net_worth) * 100 if net_worth > 0 else 0

        fixed_breakdown = comp["fixed_assets"]
        fixed_breakdown_pct = {
            "type_real_estate": (fixed_breakdown["real_estate"] / fixed_total) * 100 if fixed_total > 0 else 0,
            "type_vehicles": (fixed_breakdown["vehicles"] / fixed_total) * 100 if fixed_total > 0 else 0,
            "type_other_assets": (fixed_breakdown["other_assets"] / fixed_total) * 100 if fixed_total > 0 else 0,
            "type_gold": (comp["gold_value_egp"] / net_worth) * 100 if net_worth > 0 else 0,
        }

        return {
            "total_fixed_assets_value": round(fixed_total, 2),
            "liquid_assets_value": round(liquid_total, 2),
            "total_net_worth": round(net_worth, 2),
            "fixed_assets_ratio": round(fixed_ratio, 2),
            "liquid_assets_ratio": round(liquid_ratio, 2),
            "net_worth_contribution": round(fixed_ratio, 2),
            "totalFixedAssetsValue": round(fixed_total, 2),
            "liquidAssetsValue": round(liquid_total, 2),
            "totalNetWorth": round(net_worth, 2),
            "fixedAssetsRatio": round(fixed_ratio, 2),
            "liquidAssetsRatio": round(liquid_ratio, 2),
            "netWorthContribution": round(fixed_ratio, 2),
            "fixed_assets_breakdown": {
                "type_real_estate": round(fixed_breakdown["real_estate"], 2),
                "type_vehicles": round(fixed_breakdown["vehicles"], 2),
                "type_other_assets": round(fixed_breakdown["other_assets"], 2),
            },
            "fixed_assets_breakdown_pct": {
                key: round(value, 2) for key, value in fixed_breakdown_pct.items()
            },
            "portfolio_distribution": {
                "liquid_assets": round(liquid_total, 2),
                "fixed_assets": round(fixed_total, 2),
            },
        }

    def certificate_forecast_payload(self, today: date | None = None) -> dict:
        today = today or date.today()

        comp = self.portfolio_components()
        active_certs = self._active_certificates()
        rental_service = FinancialSyncService()
        monthly_rental_income = _to_float(rental_service.period_rental_income_total("month"))

        # Liquidity is calibrated from BalanceEntry cash rows only and converted to EGP via BUY rates.
        cash_balance = self._strict_liquid_assets_egp()

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
            amount_egp = self._converted_egp(_to_float(cert.amount), code, comp["rates"])
            interest_egp = self._converted_egp(_to_float(cert.interest_value), code, comp["rates"])

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

        investment_recommendations: List[object] = []
        financial_recommendations: List[str] = []
        investment_recommendation_details: List[dict] = []
        financial_recommendation_details: List[dict] = []

        def _fmt_money(value: float) -> str:
            return f"{value:,.2f}"

        def _fmt_pct(value: float, digits: int = 2) -> str:
            return f"{value:.{digits}f}"

        def _add_investment_recommendation(
            rec: object,
            reason_key: str,
            reason_params: Dict[str, float | int],
            text: str,
            reason_text: str,
            priority: str = "medium",
        ) -> None:
            investment_recommendations.append(rec)
            key = rec.get("key") if isinstance(rec, dict) else str(rec)
            params: Dict[str, float | int] = {}
            if isinstance(rec, dict):
                for field in ["days_left"]:
                    if field in rec:
                        params[field] = cast(float | int, rec[field])
            investment_recommendation_details.append(
                {
                    "key": key,
                    "params": params,
                    "reason_key": reason_key,
                    "reason_params": reason_params,
                    "text": text,
                    "reason_text": reason_text,
                    "priority": priority,
                }
            )

        def _add_financial_recommendation(
            key: str,
            reason_key: str,
            reason_params: Dict[str, float | int],
            text: str,
            reason_text: str,
            priority: str,
        ) -> None:
            self._append_unique(financial_recommendations, key)
            financial_recommendation_details.append(
                {
                    "key": key,
                    "params": {},
                    "reason_key": reason_key,
                    "reason_params": reason_params,
                    "text": text,
                    "reason_text": reason_text,
                    "priority": priority,
                }
            )

        if nearest_maturity is not None:
            if nearest_maturity <= 7:
                _add_investment_recommendation(
                    {"key": "recommend_maturity_very_soon", "days_left": nearest_maturity},
                    "recommend_reason_maturity_window",
                    {
                        "days_left": nearest_maturity,
                        "forecast_30": round(forecast_30, 2),
                        "forecast_90": round(forecast_90, 2),
                    },
                    text=(
                        f"A certificate matures in {nearest_maturity} days. "
                        f"Expected inflow: {_fmt_money(forecast_30)} EGP (30d), {_fmt_money(forecast_90)} EGP (90d)."
                    ),
                    reason_text=(
                        f"Short maturity window improves near-term liquidity planning with a visible 90-day inflow pipeline "
                        f"of {_fmt_money(forecast_90)} EGP."
                    ),
                    priority="high",
                )
            elif nearest_maturity <= 30:
                _add_investment_recommendation(
                    {"key": "recommend_maturity_soon", "days_left": nearest_maturity},
                    "recommend_reason_maturity_window",
                    {
                        "days_left": nearest_maturity,
                        "forecast_30": round(forecast_30, 2),
                        "forecast_90": round(forecast_90, 2),
                    },
                    text=(
                        f"A certificate matures in {nearest_maturity} days. "
                        f"Expected inflow: {_fmt_money(forecast_30)} EGP (30d), {_fmt_money(forecast_90)} EGP (90d)."
                    ),
                    reason_text=(
                        "The maturity profile supports liquidity and optional reinvestment decisions over the next quarter."
                    ),
                    priority="medium",
                )

        if forecast_90 > (forecast_30 + max(obligations_30, 1)) * 1.8:
            _add_investment_recommendation(
                "recommend_large_maturity_90",
                "recommend_reason_large_maturity",
                {
                    "forecast_30": round(forecast_30, 2),
                    "forecast_90": round(forecast_90, 2),
                    "forecast_180": round(forecast_180, 2),
                },
                text=(
                    f"Maturity inflows are front-loaded to the coming quarter: "
                    f"30d {_fmt_money(forecast_30)} EGP, 90d {_fmt_money(forecast_90)} EGP, 180d {_fmt_money(forecast_180)} EGP."
                ),
                reason_text=(
                    "You can stage renewals and diversification gradually instead of concentrating decisions on a single date."
                ),
                priority="medium",
            )

        liquidity_coverage_90 = cash_balance / obligations_90 if obligations_90 > 0 else 999.0
        maturity_support_30 = (cash_balance + forecast_30 + monthly_rental_income) / obligations_30 if obligations_30 > 0 else 999.0
        low_liquidity_flag = obligations_30 > 0 and (
            (cash_balance < obligations_90 * 0.85 and (cash_balance + forecast_30) < obligations_90)
            or (liquidity_coverage_90 < 1.1 and maturity_support_30 < 1.0)
        )

        future_cash_30 = cash_balance + forecast_30 + monthly_rental_income
        future_cash_90 = cash_balance + forecast_90 + (monthly_rental_income * 3)
        future_cash_180 = cash_balance + forecast_180 + (monthly_rental_income * 6)

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
            gold_trend_7 = self._gold_trend_change(gold_history, 7)
            gold_trend_30 = self._gold_trend_change(gold_history, 30)
            gold_trend_90 = self._gold_trend_change(gold_history, 90)
            gold_trend_365 = self._gold_trend_change(gold_history, 365)

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

        if cash_coverage_months is not None and cash_coverage_months < 3:
            low_liquidity_flag = True

        if low_liquidity_flag:
            _add_financial_recommendation(
                "recommend_low_liquidity",
                "recommend_reason_liquidity_pressure",
                {
                    "liquid_assets": round(cash_balance, 2),
                    "monthly_expenses": round(avg_monthly_expenses, 2),
                    "cash_coverage": round(cash_coverage_months or 0, 1),
                    "future_cash_30": round(future_cash_30, 2),
                    "future_cash_90": round(future_cash_90, 2),
                },
                text=(
                    f"Liquidity is tight: liquid assets {_fmt_money(cash_balance)} EGP cover about "
                    f"{_fmt_pct(cash_coverage_months or 0, 1)} months of expenses."
                ),
                reason_text=(
                    f"Monthly expenses are {_fmt_money(avg_monthly_expenses)} EGP, while projected cash is "
                    f"{_fmt_money(future_cash_30)} EGP (30d) and {_fmt_money(future_cash_90)} EGP (90d)."
                ),
                priority="high",
            )

        if cash_coverage_months is not None and cash_coverage_months < 3:
            _add_financial_recommendation(
                "recommend_low_emergency_fund",
                "recommend_reason_cash_coverage",
                {
                    "liquid_assets": round(cash_balance, 2),
                    "monthly_expenses": round(avg_monthly_expenses, 2),
                    "cash_coverage": round(cash_coverage_months, 1),
                },
                text=(
                    f"Emergency coverage is below target at {_fmt_pct(cash_coverage_months, 1)} months."
                ),
                reason_text=(
                    "Build a larger reserve before increasing risk exposure in gold or long-dated allocations."
                ),
                priority="high",
            )

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
            f"7d {_fmt_pct(gold_trend_7)}%, 30d {_fmt_pct(gold_trend_30)}%, 90d {_fmt_pct(gold_trend_90)}%, "
            f"MA(7) {_fmt_money(gold_ma_short)}, MA(30) {_fmt_money(gold_ma_long)}, gap {_fmt_pct(gold_ma_gap_pct)}%."
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
            gold_text += f" Current gold weight {_fmt_pct(gold_ratio)}% is low versus portfolio risk-balancing needs."
        elif gold_ratio > 28:
            gold_text += f" Current gold weight {_fmt_pct(gold_ratio)}% is elevated; avoid increasing concentration."

        _add_investment_recommendation(
            {
                "key": "recommend_gold_dynamic",
                "trend": gold_trend_state,
            },
            "recommend_reason_gold_signal",
            gold_reason_params,
            text=gold_text,
            reason_text=(
                f"Gold signal {_fmt_pct(gold_signal)} with volatility {_fmt_pct(gold_volatility)}%; "
                f"current allocation {_fmt_pct(gold_ratio)}%."
            ),
            priority="medium" if gold_trend_state in {"Strong Uptrend", "Strong Downtrend", "High Volatility"} else "low",
        )

        net_income_buffer = total_monthly_income - avg_monthly_expenses
        projected_obligation_cover_90 = (future_cash_90 / obligations_90) if obligations_90 > 0 else 999.0
        liquidity_strength = (cash_coverage_months or 0.0)

        strengths: List[str] = []
        if liquidity_strength >= 6:
            strengths.append(f"liquidity coverage is {_fmt_pct(liquidity_strength, 1)} months")
        if net_income_buffer > 0:
            strengths.append(f"monthly surplus is {_fmt_money(net_income_buffer)} EGP")
        if comp["net_worth_egp"] > 0 and fixed_assets_ratio >= 20:
            strengths.append(f"net worth is {_fmt_money(comp['net_worth_egp'])} EGP with diversified fixed assets")
        if future_cash_90 >= cash_balance:
            strengths.append("future cash projection is stable to improving over 90 days")

        pressure_points: List[str] = []
        if low_liquidity_flag:
            pressure_points.append("near-term liquidity pressure is elevated")
        if net_income_buffer < 0:
            pressure_points.append(f"monthly cash flow is negative by {_fmt_money(abs(net_income_buffer))} EGP")
        if projected_obligation_cover_90 < 1.0:
            pressure_points.append("90-day cash projection does not fully cover expected obligations")
        if certificate_income_ratio > 45:
            pressure_points.append(
                f"income is concentrated in certificates ({_fmt_pct(certificate_income_ratio, 1)}% of recurring income)"
            )

        if strengths:
            _add_financial_recommendation(
                "recommend_asset_allocation_balanced",
                "recommend_reason_balanced_portfolio",
                {
                    "cash_ratio": round(cash_ratio, 1),
                    "certificate_ratio": round(certificate_ratio, 1),
                    "gold_ratio": round(gold_ratio, 1),
                },
                text=(
                    "Overall financial health is "
                    + ("strong" if len(strengths) >= 3 and not pressure_points else "stable")
                    + ": "
                    + "; ".join(strengths[:3])
                    + "."
                ),
                reason_text=(
                    f"Allocation mix: cash {_fmt_pct(cash_ratio, 1)}%, certificates {_fmt_pct(certificate_ratio, 1)}%, "
                    f"gold {_fmt_pct(gold_ratio, 1)}%, fixed assets {_fmt_pct(fixed_assets_ratio, 1)}%."
                ),
                priority="low",
            )

        if pressure_points:
            _add_financial_recommendation(
                "recommend_low_liquidity" if low_liquidity_flag else "recommend_cashflow_attention",
                "recommend_reason_liquidity_pressure",
                {
                    "liquid_assets": round(cash_balance, 2),
                    "monthly_expenses": round(avg_monthly_expenses, 2),
                    "cash_coverage": round(cash_coverage_months or 0, 1),
                    "future_cash_30": round(future_cash_30, 2),
                    "future_cash_90": round(future_cash_90, 2),
                },
                text=(
                    "Financial pressure points need attention: " + "; ".join(pressure_points[:3]) + "."
                ),
                reason_text=(
                    "Prioritize short-term resilience before increasing long-term risk allocations."
                ),
                priority="high" if low_liquidity_flag else "medium",
            )

        dominant_non_cash_ratio = max(certificate_ratio, gold_ratio, fixed_assets_ratio, foreign_currency_ratio)
        excess_liquidity = (
            not low_liquidity_flag
            and cash_coverage_months is not None
            and cash_coverage_months > 10
            and (cash_ratio > dominant_non_cash_ratio + 8 or cash_ratio > 55)
        )
        if excess_liquidity:
            _add_financial_recommendation(
                "recommend_idle_cash",
                "recommend_reason_excess_liquidity",
                {
                    "liquid_assets": round(cash_balance, 2),
                    "monthly_expenses": round(avg_monthly_expenses, 2),
                    "cash_coverage": round(cash_coverage_months or 0, 1),
                },
                text=(
                    f"Liquidity is comfortably above requirements ({_fmt_pct(cash_coverage_months or 0, 1)} months); "
                    "consider deploying part of excess cash gradually into diversified return-generating assets."
                ),
                reason_text=(
                    f"Cash weight is {_fmt_pct(cash_ratio, 1)}% versus certificates {_fmt_pct(certificate_ratio, 1)}% "
                    f"and gold {_fmt_pct(gold_ratio, 1)}%."
                ),
                priority="medium",
            )

        if foreign_currency_ratio > max(certificate_ratio, gold_ratio) + 10 and foreign_currency_ratio > 30:
            _add_financial_recommendation(
                "recommend_high_foreign_currency_exposure",
                "recommend_reason_foreign_exposure",
                {
                    "foreign_ratio": round(foreign_currency_ratio, 1),
                    "gold_ratio": round(gold_ratio, 1),
                    "certificate_ratio": round(certificate_ratio, 1),
                },
                text=(
                    f"Foreign-currency exposure is elevated at {_fmt_pct(foreign_currency_ratio, 1)}%; "
                    "rebalance gradually to reduce concentration risk."
                ),
                reason_text=(
                    f"Current mix vs alternatives: gold {_fmt_pct(gold_ratio, 1)}%, certificates {_fmt_pct(certificate_ratio, 1)}%."
                ),
                priority="medium",
            )

        dominant_ratio = max(cash_ratio, foreign_currency_ratio, certificate_ratio, gold_ratio, fixed_assets_ratio)
        if certificate_ratio == dominant_ratio and certificate_ratio > 35 and (certificate_ratio - max(cash_ratio, gold_ratio, foreign_currency_ratio)) > 12:
            _add_financial_recommendation(
                "recommend_certificate_concentration",
                "recommend_reason_certificate_concentration",
                {
                    "certificate_ratio": round(certificate_ratio, 1),
                    "cash_ratio": round(cash_ratio, 1),
                    "gold_ratio": round(gold_ratio, 1),
                },
                text=(
                    f"Certificate allocation is concentrated at {_fmt_pct(certificate_ratio, 1)}%; "
                    "reduce single-asset dependence by rebalancing future maturities."
                ),
                reason_text=(
                    f"Relative weights are cash {_fmt_pct(cash_ratio, 1)}% and gold {_fmt_pct(gold_ratio, 1)}%."
                ),
                priority="medium",
            )

        min_certificate_ratio = max(8.0, min(20.0, (gold_ratio + fixed_assets_ratio) * 0.25))
        if certificate_ratio < min_certificate_ratio:
            _add_financial_recommendation(
                "recommend_low_certificate_allocation",
                "recommend_reason_low_certificate_allocation",
                {
                    "certificate_ratio": round(certificate_ratio, 1),
                    "target_ratio": round(min_certificate_ratio, 1),
                },
                text=(
                    f"Certificate allocation is {_fmt_pct(certificate_ratio, 1)}%, below the target band around "
                    f"{_fmt_pct(min_certificate_ratio, 1)}%."
                ),
                reason_text=(
                    "A moderate increase in certificates can improve income stability and reduce return volatility."
                ),
                priority="medium",
            )

        if not financial_recommendations:
            _add_financial_recommendation(
                "recommend_asset_allocation_balanced",
                "recommend_reason_balanced_portfolio",
                {
                    "cash_ratio": round(cash_ratio, 1),
                    "certificate_ratio": round(certificate_ratio, 1),
                    "gold_ratio": round(gold_ratio, 1),
                },
                text="Financial position is balanced with healthy liquidity, income coverage, and diversified assets.",
                reason_text=(
                    f"Cash {_fmt_pct(cash_ratio, 1)}%, certificates {_fmt_pct(certificate_ratio, 1)}%, gold {_fmt_pct(gold_ratio, 1)}%, "
                    f"fixed assets {_fmt_pct(fixed_assets_ratio, 1)}%."
                ),
                priority="low",
            )

        action_plan: dict = {}
        available_capital = max(cash_balance + forecast_30, 0.0)
        if available_capital <= 0:
            available_capital = max(total_monthly_income, 0.0)

        income_loss_ratio = (maturing_interest_30 / total_monthly_income) * 100 if total_monthly_income > 0 else 0
        if income_loss_ratio > 20 and certificate_balance > 0:
            action_plan = {"key": "action_renew_certificate"}
        elif low_liquidity_flag:
            action_plan = {
                "key": "action_gold_cash",
                "gold_amount": round(available_capital * 0.20, 0),
                "cash_amount": round(available_capital * 0.80, 0),
            }
        elif certificate_ratio > 40 or certificate_income_ratio > 30:
            action_plan = {
                "key": "action_gold_certificate_cash",
                "gold_amount": round(available_capital * 0.30, 0),
                "certificate_amount": round(available_capital * 0.35, 0),
                "cash_amount": round(available_capital * 0.35, 0),
            }
        elif gold_signal >= 6:
            action_plan = {
                "key": "action_gold_certificate",
                "gold_amount": round(available_capital * 0.60, 0),
                "certificate_amount": round(available_capital * 0.40, 0),
            }
        elif gold_signal <= -6:
            action_plan = {
                "key": "action_gold_certificate_cash",
                "gold_amount": round(available_capital * 0.20, 0),
                "certificate_amount": round(available_capital * 0.45, 0),
                "cash_amount": round(available_capital * 0.35, 0),
            }
        elif available_capital > 0:
            action_plan = {
                "key": "action_gold_cash",
                "gold_amount": round(available_capital * 0.50, 0),
                "cash_amount": round(available_capital * 0.50, 0),
            }

        # Recommended action must never be empty.
        if not action_plan:
            if certificate_balance > 0:
                action_plan = {"key": "action_renew_certificate"}
            else:
                action_plan = {
                    "key": "action_gold_cash",
                    "gold_amount": 0,
                    "cash_amount": 0,
                }

        action_reason_key = "action_reason_rebalance_mix"
        if action_plan.get("key") == "action_renew_certificate":
            action_reason_key = "action_reason_renew_certificate"
        elif low_liquidity_flag:
            action_reason_key = "action_reason_liquidity_protection"
        elif gold_signal >= neutral_band or gold_signal <= -neutral_band:
            action_reason_key = "action_reason_gold_tilt"

        action_reason_text = (
            f"Allocation context: cash {_fmt_pct(cash_ratio, 1)}%, gold {_fmt_pct(gold_ratio, 1)}%, "
            f"certificates {_fmt_pct(certificate_ratio, 1)}%. "
        )
        if action_plan.get("key") == "action_renew_certificate":
            action_reason_text += (
                f"Certificate maturity impact on income is material ({_fmt_pct(income_loss_ratio, 1)}% of monthly income), "
                "so preserving income continuity is prioritized."
            )
        elif low_liquidity_flag:
            action_reason_text += (
                f"Liquidity protection takes priority because cash coverage is {_fmt_pct(cash_coverage_months or 0, 1)} months "
                f"with near-term projected cash {_fmt_money(future_cash_30)} EGP (30d)."
            )
        elif gold_trend_state in {"Strong Uptrend", "Moderate Uptrend", "Strong Downtrend", "Moderate Downtrend", "High Volatility"}:
            action_reason_text += (
                f"Gold signal is {_fmt_pct(gold_signal)} ({gold_trend_state}), so the split is aimed at balancing trend opportunity "
                "with concentration and liquidity risk."
            )
        else:
            action_reason_text += "Portfolio is broadly balanced, so this action keeps diversification while preserving flexibility."

        action_plan["reason_key"] = action_reason_key
        action_plan["reason_params"] = {
            "cash_ratio": round(cash_ratio, 1),
            "gold_ratio": round(gold_ratio, 1),
            "certificate_ratio": round(certificate_ratio, 1),
            "cash_coverage": round(cash_coverage_months or 0, 1),
            "gold_signal": round(gold_signal, 2),
        }
        action_plan["reason_text"] = action_reason_text

        snapshot = self.fixed_assets_snapshot()

        return {
            "cash_balance": round(cash_balance, 2),
            "certificate_balance": round(certificate_balance, 2),
            "fixed_assets_balance": round(comp["fixed_assets_total_egp"], 2),
            "net_worth": round(comp["net_worth_egp"], 2),
            "future_cash_30": round(future_cash_30, 2),
            "future_cash_90": round(future_cash_90, 2),
            "future_cash_180": round(future_cash_180, 2),
            "forecast_30": round(forecast_30, 2),
            "forecast_90": round(forecast_90, 2),
            "forecast_180": round(forecast_180, 2),
            "upcoming": upcoming[:10],
            "cash_ratio": round(cash_ratio, 1),
            "foreign_currency_ratio": round(foreign_currency_ratio, 1),
            "certificate_ratio": round(certificate_ratio, 1),
            "gold_ratio": round(gold_ratio, 1),
            "fixed_assets_ratio": round(fixed_assets_ratio, 1),
            "real_estate_ratio": round(snapshot["fixed_assets_breakdown_pct"]["type_real_estate"], 1),
            "vehicles_ratio": round(snapshot["fixed_assets_breakdown_pct"]["type_vehicles"], 1),
            "other_assets_ratio": round(snapshot["fixed_assets_breakdown_pct"]["type_other_assets"], 1),
            "gold_value": round(comp["gold_value_egp"], 2),
            "gold_grams": round(comp["gold_grams"], 3),
            "gold_trend_pct": round(gold_trend_pct, 2),
            "investment_recommendations": investment_recommendations,
            "financial_recommendations": financial_recommendations,
            "action_plan": action_plan,
            "monthly_salary": round(monthly_salary, 2),
            "monthly_certificate_income": round(monthly_certificate_income, 2),
            "monthly_rental_income": round(monthly_rental_income, 2),
            "total_monthly_income": round(total_monthly_income, 2),
            "certificate_income_ratio": round(certificate_income_ratio, 1),
            "gold_trend_30": round(gold_trend_30, 2),
            "gold_trend_90": round(gold_trend_90, 2),
            "gold_trend_365": round(gold_trend_365, 2),
            "gold_trend_7": round(gold_trend_7, 2),
            "gold_ma_short": round(gold_ma_short, 2),
            "gold_ma_long": round(gold_ma_long, 2),
            "gold_ma_gap_pct": round(gold_ma_gap_pct, 2),
            "gold_signal": round(gold_signal, 2),
            "avg_monthly_expenses": round(avg_monthly_expenses, 2),
            "cash_coverage_months": round(cash_coverage_months, 1) if cash_coverage_months is not None else None,
            "allocation_values": comp["allocation_values"],
            "allocation_percentages": comp["allocation_percentages"],
            "investment_recommendation_details": investment_recommendation_details,
            "financial_recommendation_details": financial_recommendation_details,
            "fixed_assets_snapshot": snapshot,
            "expiry_warning_days": int(AppSettings.get("cert_expiry_warning_days", "30") or 30),
        }
