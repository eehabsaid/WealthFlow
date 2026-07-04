from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Tuple

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
    SalaryEntry,
    _is_certificate_active,
)
from core.services.financial_sync_service import FinancialSyncService


REAL_ESTATE_ASSET_TYPES = {"Real Estate"}
VEHICLE_ASSET_TYPES = {"Vehicles"}
OTHER_ASSET_TYPES = {"Other Assets"}


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
    def __init__(self):
        self._cache: Dict[str, object] = {}

    def _cached(self, key: str, producer):
        if key not in self._cache:
            self._cache[key] = producer()
        return self._cache[key]

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
        code = str(currency_code or "EGP").upper()
        if code in ("", "EGP"):
            return amount
        return amount * _to_float(rates.get(code))

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
                "type_cash": cash_total,
                "type_bank": banks_total,
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

        # Future cash position must stay liquid-only (EGP cash/bank rows, excluding cert/gold).
        cash_balance = 0.0
        for item in comp["entries"]:
            balance_type = str(item.get("balance_type") or "")
            code = str(item.get("currency_code") or "").upper()
            if balance_type == BalanceEntry.BalanceType.CERTIFICATE:
                continue
            if code == "GOLD":
                continue
            if code != "EGP":
                continue
            cash_balance += _to_float(item.get("amount"))

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
        total_expenses = _to_float(expenses.aggregate(total=Sum("amount"))["total"])
        months_with_expenses = len(set(expenses.values_list("year", "month")))
        avg_monthly_expenses = total_expenses / months_with_expenses if months_with_expenses > 0 else 0

        monthly_certificate_income = _to_float(comp["certificate_interest_total_egp"])
        latest_salary = SalaryEntry.objects.filter(paid__gt=0).order_by("-year", "-id").first()
        monthly_salary = _to_float(latest_salary.paid) if latest_salary else 0
        total_monthly_income = monthly_salary + monthly_certificate_income + monthly_rental_income

        cash_coverage_months = cash_balance / avg_monthly_expenses if avg_monthly_expenses > 0 else None
        certificate_income_ratio = (monthly_certificate_income / total_monthly_income) * 100 if total_monthly_income > 0 else 0

        investment_recommendations: List[object] = []
        financial_recommendations: List[str] = []

        if certificate_ratio > 70:
            financial_recommendations.append("recommend_certificate_concentration")
        if fixed_assets_ratio > 70:
            financial_recommendations.append("recommend_certificate_concentration")

        if nearest_maturity is not None:
            if nearest_maturity <= 7:
                investment_recommendations.append({"key": "recommend_maturity_very_soon", "days_left": nearest_maturity})
            elif nearest_maturity <= 30:
                investment_recommendations.append({"key": "recommend_maturity_soon", "days_left": nearest_maturity})

        if forecast_90 > forecast_30 * 2:
            investment_recommendations.append("recommend_large_maturity_90")

        liquidity_ratio = (forecast_30 / forecast_180) * 100 if forecast_180 > 0 else 0
        low_liquidity_flag = forecast_180 > 0 and liquidity_ratio < 25
        if low_liquidity_flag:
            financial_recommendations.append("recommend_low_liquidity")

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

        gold_trend_30 = 0
        gold_trend_90 = 0
        gold_trend_365 = 0
        gold_history = list(GoldPriceHistory.objects.order_by("-timestamp")[:250])

        if len(gold_history) > 30:
            latest = _to_float(gold_history[0].carat_21k)
            old_30 = _to_float(gold_history[29].carat_21k)
            if old_30:
                gold_trend_30 = ((latest - old_30) / old_30) * 100
        if len(gold_history) > 90:
            latest = _to_float(gold_history[0].carat_21k)
            old_90 = _to_float(gold_history[89].carat_21k)
            if old_90:
                gold_trend_90 = ((latest - old_90) / old_90) * 100
        if len(gold_history) > 250:
            latest = _to_float(gold_history[0].carat_21k)
            old_365 = _to_float(gold_history[249].carat_21k)
            if old_365:
                gold_trend_365 = ((latest - old_365) / old_365) * 100

        if cash_ratio > 40 and not low_liquidity_flag:
            financial_recommendations.append("recommend_idle_cash")

        if cash_ratio > 60 and not low_liquidity_flag:
            financial_recommendations.append("recommend_high_cash_position")
        if foreign_currency_ratio > 40:
            financial_recommendations.append("recommend_high_foreign_currency_exposure")

        if cash_coverage_months is not None:
            if cash_coverage_months < 3:
                low_liquidity_flag = True
                financial_recommendations.append("recommend_low_emergency_fund")
            elif cash_coverage_months > 12 and cash_ratio > 25 and not low_liquidity_flag:
                financial_recommendations.append("recommend_excess_cash")

        if gold_trend_30 > 15:
            investment_recommendations.append("recommend_gold_strong_uptrend")
        elif gold_trend_30 > 5:
            investment_recommendations.append("recommend_gold_uptrend")
        elif gold_trend_30 < -15:
            investment_recommendations.append("recommend_gold_strong_downtrend")
        elif gold_trend_30 < -5:
            investment_recommendations.append("recommend_gold_downtrend")
        else:
            investment_recommendations.append("recommend_gold_neutral")

        if certificate_ratio < 20:
            financial_recommendations.append("recommend_low_certificate_allocation")

        if not financial_recommendations:
            financial_recommendations.append("recommend_asset_allocation_balanced")

        action_plan = ""
        if forecast_30 > 0:
            available_capital = cash_balance + forecast_30
            income_loss_ratio = (maturing_interest_30 / total_monthly_income) * 100 if total_monthly_income > 0 else 0
            if income_loss_ratio > 20:
                action_plan = {"key": "action_renew_certificate"}
            elif certificate_ratio > 45 or certificate_income_ratio > 30:
                if gold_trend_365 > 15 and gold_trend_30 < -10:
                    action_plan = {
                        "key": "action_gold_certificate_cash",
                        "gold_amount": round(available_capital * 0.40, 0),
                        "certificate_amount": round(available_capital * 0.30, 0),
                        "cash_amount": round(available_capital * 0.30, 0),
                    }
                elif gold_trend_365 > 15 and gold_trend_30 > 0:
                    action_plan = {
                        "key": "action_gold_certificate_cash",
                        "gold_amount": round(available_capital * 0.60, 0),
                        "certificate_amount": round(available_capital * 0.20, 0),
                        "cash_amount": round(available_capital * 0.20, 0),
                    }
                elif gold_trend_365 < 5:
                    action_plan = {
                        "key": "action_gold_certificate_cash",
                        "gold_amount": round(available_capital * 0.20, 0),
                        "certificate_amount": round(available_capital * 0.50, 0),
                        "cash_amount": round(available_capital * 0.30, 0),
                    }
            elif gold_ratio < 10:
                if gold_trend_30 < -15:
                    gold_amount = round(available_capital * 0.80, 0)
                    cash_amount = round(available_capital * 0.20, 0)
                elif gold_trend_30 < -5:
                    gold_amount = round(available_capital * 0.70, 0)
                    cash_amount = round(available_capital * 0.30, 0)
                else:
                    gold_amount = round(available_capital * 0.60, 0)
                    cash_amount = round(available_capital * 0.40, 0)
                action_plan = {
                    "key": "action_gold_cash",
                    "gold_amount": gold_amount,
                    "cash_amount": cash_amount,
                }
            else:
                action_plan = {
                    "key": "action_gold_certificate",
                    "gold_amount": round(available_capital * 0.50, 0),
                    "certificate_amount": round(available_capital * 0.50, 0),
                }

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
            "avg_monthly_expenses": round(avg_monthly_expenses, 2),
            "cash_coverage_months": round(cash_coverage_months, 1) if cash_coverage_months is not None else None,
            "allocation_values": comp["allocation_values"],
            "allocation_percentages": comp["allocation_percentages"],
            "fixed_assets_snapshot": snapshot,
            "expiry_warning_days": int(AppSettings.get("cert_expiry_warning_days", "30") or 30),
        }
