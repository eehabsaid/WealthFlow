"""
Related-object lookups and derived financial metrics for FixedAsset.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist


class FixedAssetCalculationsMixin:
    def _safe_related(self, attr_name):
        try:
            return getattr(self, attr_name)
        except ObjectDoesNotExist:
            return None
        except Exception:
            return None

    def _get_related_details(self):
        type_map = {
            "Real Estate": "real_estate",
            "Vehicles": "vehicle_details",
            "Gold": "gold_details",
            "Other Assets": "other_asset_details",
        }
        relation_name = type_map.get(self.asset_type)
        if not relation_name:
            return None
        return self._safe_related(relation_name)

    def get_total_acquisition_costs(self):
        if self.asset_type == "Real Estate":
            return sum(item.amount_egp for item in self.acquisition_costs.all())
        return Decimal("0")

    def get_total_renovation_costs(self):
        if self.asset_type == "Real Estate":
            return sum(item.amount_egp for item in self.renovations.all())
        return Decimal("0")

    def get_total_investment(self):
        return self.purchase_price + self.get_total_acquisition_costs() + self.get_total_renovation_costs()

    def get_gain_loss(self):
        return self.current_market_value - self.get_total_investment()

    def get_roi(self):
        inv = self.get_total_investment()
        if inv > 0:
            return (self.get_gain_loss() / inv) * 100
        return Decimal("0")

    def get_appreciation(self):
        inv = self.get_total_investment()
        if inv > 0:
            return (self.get_gain_loss() / inv) * 100
        return Decimal("0")

    def get_annual_return(self):
        inv = self.get_total_investment()
        if inv <= 0 or not self.purchase_date:
            return Decimal("0")
        from datetime import date
        today = date.today()
        purchase_date = self.purchase_date
        if isinstance(purchase_date, str):
            from datetime import datetime
            try:
                purchase_date = datetime.strptime(purchase_date.split("T")[0], "%Y-%m-%d").date()
            except ValueError:
                return Decimal("0")
        diff_days = (today - purchase_date).days
        holding_years = diff_days / 365.25
        if holding_years <= 0:
            return Decimal("0")
        try:
            return Decimal(str((float(self.current_market_value / inv) ** (1 / holding_years) - 1) * 100))
        except Exception:
            return Decimal("0")
