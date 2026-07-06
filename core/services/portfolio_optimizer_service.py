from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Tuple

from django.db.models import Sum

from core.models import BankCertificate, BalanceEntry, Expense, FixedAsset, _is_certificate_active
from core.services.net_worth_service import NetWorthService


def _to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


@dataclass(frozen=True)
class AllocationBand:
    min_pct: float
    max_pct: float


class PortfolioOptimizerService:
    ALLOCATION_LABELS: Dict[str, str] = {
        "cash": "portfolio_optimizer_asset_cash",
        "banks": "portfolio_optimizer_asset_banks",
        "certificates": "portfolio_optimizer_asset_certificates",
        "gold": "portfolio_optimizer_asset_gold",
        "real_estate": "portfolio_optimizer_asset_real_estate",
        "vehicles": "portfolio_optimizer_asset_vehicles",
        "other_assets": "portfolio_optimizer_asset_other_assets",
    }

    # Recommended ranges kept as constants by product requirement.
    RECOMMENDED_BANDS: Dict[str, AllocationBand] = {
        "cash": AllocationBand(15.0, 25.0),
        "banks": AllocationBand(5.0, 15.0),
        "certificates": AllocationBand(15.0, 35.0),
        "gold": AllocationBand(10.0, 20.0),
        "real_estate": AllocationBand(30.0, 60.0),
        "vehicles": AllocationBand(0.0, 15.0),
        "other_assets": AllocationBand(0.0, 15.0),
    }

    def __init__(self, *, today: date | None = None):
        self.today = today or date.today()
        self.net_worth = NetWorthService()

    def _allocation_values(self, comp: dict) -> Dict[str, float]:
        values = comp.get("allocation_values", {})
        return {
            "cash": _to_float(values.get("type_cash")),
            "banks": _to_float(values.get("type_bank")),
            "certificates": _to_float(values.get("bank_certificates")),
            "gold": _to_float(values.get("type_gold")),
            "real_estate": _to_float(values.get("type_real_estate")),
            "vehicles": _to_float(values.get("type_vehicles")),
            "other_assets": _to_float(values.get("type_other_assets")),
        }

    def _allocation_percentages(self, values: Dict[str, float], total: float) -> Dict[str, float]:
        if total <= 0:
            return {key: 0.0 for key in values}
        return {key: round((value / total) * 100.0, 2) for key, value in values.items()}

    def _month_expense_baseline(self) -> Tuple[float, int]:
        start_date = self.today - timedelta(days=180)
        qs = Expense.objects.filter(date__gte=start_date)
        total = _to_float(qs.aggregate(total=Sum("amount")).get("total"))
        active_months = len(set(qs.values_list("year", "month")))
        return total, active_months

    def _monthly_expense_average(self) -> float:
        total, active_months = self._month_expense_baseline()
        if active_months > 0:
            return total / active_months
        if total > 0:
            return total / 6.0
        return 0.0

    def _score_range_metric(self, value_pct: float, low: float, high: float) -> float:
        if low <= value_pct <= high:
            return 100.0
        spread = max(high - low, 1.0)
        if value_pct < low:
            distance = low - value_pct
        else:
            distance = value_pct - high
        penalty = min(100.0, (distance / spread) * 120.0)
        return max(0.0, 100.0 - penalty)

    def _emergency_fund_months(self, liquid_value: float, monthly_expenses: float) -> float:
        if monthly_expenses <= 0:
            return 12.0
        return liquid_value / monthly_expenses

    def _score_emergency_fund(self, months: float) -> float:
        if months >= 6.0:
            return 100.0
        return max(0.0, min(100.0, (months / 6.0) * 100.0))

    def _score_diversification(self, percentages: Dict[str, float]) -> float:
        keys = [key for key in percentages if percentages[key] > 0]
        if not keys:
            return 0.0
        n = float(len(percentages))
        hhi = 0.0
        for value in percentages.values():
            share = (value / 100.0)
            hhi += share * share
        min_hhi = 1.0 / n
        max_hhi = 1.0
        if max_hhi == min_hhi:
            return 100.0
        normalized = (max_hhi - hhi) / (max_hhi - min_hhi)
        return max(0.0, min(100.0, normalized * 100.0))

    def _status_for_band(self, pct: float, band: AllocationBand) -> Tuple[str, str]:
        if band.min_pct <= pct <= band.max_pct:
            return "good", "portfolio_optimizer_status_in_range"
        distance = 0.0
        if pct < band.min_pct:
            distance = band.min_pct - pct
        elif pct > band.max_pct:
            distance = pct - band.max_pct
        if distance <= 2.0:
            return "warning", "portfolio_optimizer_status_close"
        return "danger", "portfolio_optimizer_status_outside"

    def _allocation_cards(self, values: Dict[str, float], percentages: Dict[str, float]) -> List[dict]:
        cards: List[dict] = []
        for key in ["cash", "banks", "certificates", "gold", "real_estate", "vehicles", "other_assets"]:
            band = self.RECOMMENDED_BANDS[key]
            pct = _to_float(percentages.get(key))
            status, status_key = self._status_for_band(pct, band)
            cards.append(
                {
                    "key": key,
                    "label_key": self.ALLOCATION_LABELS[key],
                    "value": round(_to_float(values.get(key)), 2),
                    "percentage": round(pct, 2),
                    "recommended_min": band.min_pct,
                    "recommended_max": band.max_pct,
                    "status": status,
                    "status_key": status_key,
                }
            )
        return cards

    def _bank_exposure(self, comp: dict) -> List[dict]:
        rates = comp.get("rates", {})
        bank_totals: Dict[str, float] = {}

        entries = BalanceEntry.objects.select_related("currency", "bank").all()
        for entry in entries:
            if not entry.bank_id:
                continue
            bank_name = entry.bank.name if entry.bank else "-"
            code = str(entry.currency.code if entry.currency else "EGP").upper()
            amount = _to_float(entry.amount)
            if code == "EGP":
                converted = amount
            elif code == "GOLD":
                converted = 0.0
            else:
                converted = amount * _to_float(rates.get(code))
            bank_totals[bank_name] = bank_totals.get(bank_name, 0.0) + converted

        for cert in BankCertificate.objects.select_related("bank", "currency").all():
            if not _is_certificate_active(cert):
                continue
            bank_name = cert.bank.name if cert.bank else "-"
            code = str(cert.currency.code if cert.currency else "EGP").upper()
            amount = _to_float(cert.amount)
            if code == "EGP":
                converted = amount
            else:
                converted = amount * _to_float(rates.get(code))
            bank_totals[bank_name] = bank_totals.get(bank_name, 0.0) + converted

        result = [
            {"bank_name": bank_name, "value": round(value, 2)}
            for bank_name, value in bank_totals.items()
            if value > 0
        ]
        result.sort(key=lambda item: item["value"], reverse=True)
        return result

    def _currency_exposure(self, comp: dict) -> List[dict]:
        rates = comp.get("rates", {})
        totals = comp.get("totals_by_currency", {})
        rows: List[dict] = []
        for code, amount in totals.items():
            upper_code = str(code or "").upper()
            value = _to_float(amount)
            if upper_code == "GOLD":
                value = _to_float(comp.get("gold_value_egp"))
            elif upper_code != "EGP":
                value = value * _to_float(rates.get(upper_code))
            rows.append({"code": upper_code or "EGP", "value": round(value, 2)})
        rows.sort(key=lambda item: item["value"], reverse=True)
        return rows

    def _top_assets(self, comp: dict, total_portfolio: float) -> List[dict]:
        rows: List[dict] = []

        for asset in FixedAsset.objects.filter(status="Owned").order_by("-current_market_value", "name"):
            current_value = _to_float(asset.current_market_value)
            purchase_value = _to_float(asset.purchase_price)
            gain_value = current_value - purchase_value
            rows.append(
                {
                    "asset": asset.name,
                    "type": asset.asset_type,
                    "value": round(current_value, 2),
                    "portfolio_pct": round((current_value / total_portfolio) * 100.0 if total_portfolio > 0 else 0.0, 2),
                    "gain": round(gain_value, 2),
                    "gain_pct": round((gain_value / purchase_value) * 100.0, 2) if purchase_value > 0 else 0.0,
                }
            )

        for cert in BankCertificate.objects.select_related("currency", "bank").all():
            if not _is_certificate_active(cert):
                continue
            code = str(cert.currency.code if cert.currency else "EGP").upper()
            amount = _to_float(cert.amount)
            converted = amount
            if code != "EGP":
                converted = amount * _to_float(comp.get("rates", {}).get(code))
            bank_name = cert.bank.name if cert.bank else "-"
            rows.append(
                {
                    "asset": f"{bank_name} Certificate",
                    "type": "Certificates",
                    "value": round(converted, 2),
                    "portfolio_pct": round((converted / total_portfolio) * 100.0 if total_portfolio > 0 else 0.0, 2),
                    "gain": round(_to_float(cert.interest_value), 2),
                    "gain_pct": 0.0,
                }
            )

        rows.sort(key=lambda item: item["value"], reverse=True)
        return rows[:10]

    def _largest_balance_entry(self, comp: dict) -> dict:
        rates = comp.get("rates", {})
        largest = {"title": "-", "value": 0.0}
        rows = BalanceEntry.objects.select_related("currency").all()
        for row in rows:
            code = str(row.currency.code if row.currency else "EGP").upper()
            amount = _to_float(row.amount)
            if code == "EGP":
                converted = amount
            elif code == "GOLD":
                continue
            else:
                converted = amount * _to_float(rates.get(code))
            if converted > largest["value"]:
                largest = {"title": row.title or "-", "value": round(converted, 2)}
        return largest

    def _health_label_key(self, score: float) -> str:
        if score >= 90:
            return "portfolio_optimizer_health_excellent"
        if score >= 75:
            return "portfolio_optimizer_health_good"
        if score >= 60:
            return "portfolio_optimizer_health_average"
        return "portfolio_optimizer_health_attention"

    def _recommendations(self, percentages: Dict[str, float], emergency_months: float) -> List[dict]:
        recommendations: List[dict] = []

        def add(key: str, severity: str, metric_value: float | None = None):
            if any(item["key"] == key for item in recommendations):
                return
            recommendations.append(
                {
                    "key": key,
                    "severity": severity,
                    "severity_key": f"portfolio_optimizer_severity_{severity}",
                    "metric_value": round(metric_value, 2) if metric_value is not None else None,
                }
            )

        cash_pct = _to_float(percentages.get("cash"))
        gold_pct = _to_float(percentages.get("gold"))
        real_estate_pct = _to_float(percentages.get("real_estate"))
        vehicle_pct = _to_float(percentages.get("vehicles"))
        cert_pct = _to_float(percentages.get("certificates"))

        if emergency_months < 6.0:
            add("portfolio_optimizer_rec_emergency_fund_low", "high", emergency_months)
        if cash_pct > 35.0:
            add("portfolio_optimizer_rec_cash_too_high", "medium", cash_pct)
        if gold_pct < 8.0:
            add("portfolio_optimizer_rec_gold_too_low", "medium", gold_pct)
        if gold_pct > 30.0:
            add("portfolio_optimizer_rec_gold_too_high", "medium", gold_pct)
        if real_estate_pct > 70.0:
            add("portfolio_optimizer_rec_real_estate_too_high", "medium", real_estate_pct)
        if vehicle_pct > 20.0:
            add("portfolio_optimizer_rec_vehicles_too_high", "low", vehicle_pct)
        if cert_pct > 50.0:
            add("portfolio_optimizer_rec_certificates_too_high", "medium", cert_pct)

        if not recommendations:
            add("portfolio_optimizer_rec_balanced", "low")

        return recommendations

    def _opportunities(self, percentages: Dict[str, float], recommendations: List[dict], comp: dict) -> List[dict]:
        opportunities: List[dict] = []

        def add(key: str, impact_key: str, severity: str):
            if any(item["key"] == key for item in opportunities):
                return
            opportunities.append(
                {
                    "key": key,
                    "impact_key": impact_key,
                    "severity": severity,
                    "severity_key": f"portfolio_optimizer_severity_{severity}",
                }
            )

        recommendation_keys = {item["key"] for item in recommendations}

        if "portfolio_optimizer_rec_cash_too_high" in recommendation_keys:
            add("portfolio_optimizer_opp_reduce_idle_cash", "portfolio_optimizer_opp_impact_idle_cash", "medium")
        if "portfolio_optimizer_rec_certificates_too_high" in recommendation_keys:
            add("portfolio_optimizer_opp_diversify_certificates", "portfolio_optimizer_opp_impact_reduce_concentration", "low")
        if "portfolio_optimizer_rec_gold_too_low" in recommendation_keys:
            add("portfolio_optimizer_opp_increase_gold", "portfolio_optimizer_opp_impact_gold_balance", "medium")
        if "portfolio_optimizer_rec_vehicles_too_high" in recommendation_keys:
            add("portfolio_optimizer_opp_reduce_vehicle_exposure", "portfolio_optimizer_opp_impact_rebalance_assets", "low")

        mortgage_total = _to_float(
            comp.get("fixed_assets", {}).get("real_estate", 0)
        )
        if mortgage_total > 0:
            add("portfolio_optimizer_opp_improve_liquidity", "portfolio_optimizer_opp_impact_cash_buffer", "low")

        return opportunities[:5]

    def payload(self) -> dict:
        comp = self.net_worth.portfolio_components()
        total_portfolio = _to_float(comp.get("net_worth_egp"))
        allocation_values = self._allocation_values(comp)
        allocation_percentages = self._allocation_percentages(allocation_values, total_portfolio)

        monthly_expenses = self._monthly_expense_average()
        liquid_for_emergency = allocation_values["cash"] + allocation_values["banks"] + allocation_values["certificates"]
        emergency_months = self._emergency_fund_months(liquid_for_emergency, monthly_expenses)

        liquidity_metric = self._score_range_metric(
            _to_float(allocation_percentages.get("cash")) + _to_float(allocation_percentages.get("banks")),
            15.0,
            30.0,
        )
        fixed_metric = self._score_range_metric(
            _to_float(allocation_percentages.get("real_estate"))
            + _to_float(allocation_percentages.get("vehicles"))
            + _to_float(allocation_percentages.get("other_assets")),
            40.0,
            70.0,
        )
        gold_metric = self._score_range_metric(_to_float(allocation_percentages.get("gold")), 10.0, 20.0)
        emergency_metric = self._score_emergency_fund(emergency_months)
        diversification_metric = self._score_diversification(allocation_percentages)

        weighted_score = (
            (liquidity_metric * 0.25)
            + (fixed_metric * 0.20)
            + (gold_metric * 0.15)
            + (emergency_metric * 0.20)
            + (diversification_metric * 0.20)
        )
        health_score = round(max(0.0, min(100.0, weighted_score)), 1)

        allocation_cards = self._allocation_cards(allocation_values, allocation_percentages)

        categories_owned = len([value for value in allocation_values.values() if value > 0])
        bank_exposure = self._bank_exposure(comp)
        currency_exposure = self._currency_exposure(comp)
        top_assets = self._top_assets(comp, total_portfolio)
        largest_balance = self._largest_balance_entry(comp)

        largest_category_key = (
            max(allocation_percentages, key=lambda key: allocation_percentages.get(key, 0.0))
            if allocation_percentages
            else "cash"
        )
        largest_category_pct = _to_float(allocation_percentages.get(largest_category_key))
        largest_category_label = self.ALLOCATION_LABELS.get(largest_category_key, "portfolio_optimizer_asset_cash")

        largest_bank = bank_exposure[0] if bank_exposure else {"bank_name": "-", "value": 0.0}
        largest_currency = currency_exposure[0] if currency_exposure else {"code": "EGP", "value": 0.0}
        largest_asset = top_assets[0] if top_assets else {"asset": "-", "value": 0.0}

        recommendations = self._recommendations(allocation_percentages, emergency_months)
        opportunities = self._opportunities(allocation_percentages, recommendations, comp)

        chart_labels = [
            self.ALLOCATION_LABELS["cash"],
            self.ALLOCATION_LABELS["banks"],
            self.ALLOCATION_LABELS["certificates"],
            self.ALLOCATION_LABELS["gold"],
            self.ALLOCATION_LABELS["real_estate"],
            self.ALLOCATION_LABELS["vehicles"],
            self.ALLOCATION_LABELS["other_assets"],
        ]
        chart_values = [
            allocation_values["cash"],
            allocation_values["banks"],
            allocation_values["certificates"],
            allocation_values["gold"],
            allocation_values["real_estate"],
            allocation_values["vehicles"],
            allocation_values["other_assets"],
        ]

        return {
            "as_of": self.today.isoformat(),
            "health": {
                "score": health_score,
                "label_key": self._health_label_key(health_score),
                "metrics": {
                    "liquidity": round(liquidity_metric, 2),
                    "fixed_assets": round(fixed_metric, 2),
                    "gold": round(gold_metric, 2),
                    "emergency_fund": round(emergency_metric, 2),
                    "diversification": round(diversification_metric, 2),
                },
            },
            "allocation": {
                "total": round(total_portfolio, 2),
                "cards": allocation_cards,
                "percentages": allocation_percentages,
            },
            "diversification": {
                "asset_classes_owned": categories_owned,
                "bank_accounts_used": len(bank_exposure),
                "largest_asset_concentration": {
                    "label_key": largest_category_label,
                    "percentage": round(largest_category_pct, 2),
                },
                "largest_bank_concentration": largest_bank,
                "largest_asset_type": largest_category_label,
                "largest_currency_exposure": largest_currency,
            },
            "recommendations": recommendations,
            "asset_breakdown": top_assets,
            "allocation_chart": {
                "labels": chart_labels,
                "values": [round(value, 2) for value in chart_values],
            },
            "concentration": {
                "largest_asset": largest_asset,
                "largest_bank": largest_bank,
                "largest_balance": largest_balance,
                "largest_exposure": {
                    "label_key": largest_category_label,
                    "value": round(_to_float(allocation_values.get(largest_category_key)), 2),
                },
                "largest_concentration_pct": round(largest_category_pct, 2),
                "warning": largest_category_pct > 50.0,
            },
            "opportunities": opportunities,
            "quality_checks": {
                "allocation_total_pct": round(sum(allocation_percentages.values()), 2),
                "recommendation_count": len(recommendations),
                "opportunity_count": len(opportunities),
            },
            "expense_baseline": {
                "avg_monthly_expenses": round(monthly_expenses, 2),
                "emergency_fund_months": round(emergency_months, 2),
            },
        }