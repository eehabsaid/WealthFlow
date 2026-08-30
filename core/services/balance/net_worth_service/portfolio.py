"""
Portfolio composition mixin for NetWorthService.

NOTE (200-line file convention): split out of the original monolithic
core/services/balance/net_worth_service.py (1162 lines). See
data_access.py for the mixin this depends on, and helpers.py for shared
utils. __init__.py assembles NetWorthService from all mixins in this
package.
"""
from __future__ import annotations

from typing import Dict

from core.models import BalanceEntry

from .helpers import _normalize_gold_purity, _to_float


class NetWorthPortfolioMixin:
    """portfolio_components, balance_payload, fixed_assets_snapshot."""

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
        from .assets.fixed_assets_snapshot import build_fixed_assets_snapshot
        return build_fixed_assets_snapshot(self.portfolio_components())
