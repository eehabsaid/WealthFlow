"""
Dict serialization for FixedAsset (to_dict()).
"""

from __future__ import annotations


class FixedAssetSerializationMixin:
    def to_dict(self):
        related_details = self._get_related_details()
        real_estate = self._safe_related("real_estate")
        vehicle_details = self._safe_related("vehicle_details")
        gold_details = self._safe_related("gold_details")
        other_asset_details = self._safe_related("other_asset_details")
        sale = self._safe_related("sale")
        mortgage = self._safe_related("mortgage")
        rental = self._safe_related("rental")
        purchase_payments = list(self.purchase_payments.all())
        first_purchase_payment = purchase_payments[0] if purchase_payments else None
        return {
            "id": self.id,
            "name": self.name,
            "asset_type": self.asset_type,
            "status": self.status,
            "purchase_date": (
                self.purchase_date.isoformat()
                if hasattr(self.purchase_date, "isoformat")
                else self.purchase_date
            ),
            "purchase_price": float(self.purchase_price),
            "purchase_usd_rate": float(self.purchase_usd_rate),
            "purchase_price_usd": float(self.purchase_price_usd),
            "current_market_value": float(self.current_market_value),
            "valuation_source": self.valuation_source,
            "last_valuation_date": (
                self.last_valuation_date.isoformat()
                if hasattr(self.last_valuation_date, "isoformat")
                else self.last_valuation_date
            ),
            "notes": self.notes,
            "purchase_currency_id": first_purchase_payment.currency_id if first_purchase_payment else None,
            "purchase_currency_code": first_purchase_payment.currency.code if first_purchase_payment and first_purchase_payment.currency else "",

            "details": related_details.to_dict() if related_details else None,

            "total_acquisition_costs": float(self.get_total_acquisition_costs()),
            "total_renovation_costs": float(self.get_total_renovation_costs()),
            "total_investment": float(self.get_total_investment()),
            "gain_loss": float(self.get_gain_loss()),
            "roi": float(self.get_roi()),
            "appreciation": float(self.get_appreciation()),
            "annual_return": float(self.get_annual_return()),

            # Related Models
            "real_estate": (
                real_estate.to_dict()
                if real_estate
                else None
            ),

            "vehicle_details": (
                vehicle_details.to_dict()
                if vehicle_details
                else None
            ),

            "gold_details": (
                gold_details.to_dict()
                if gold_details
                else None
            ),

            "other_asset_details": (
                other_asset_details.to_dict()
                if other_asset_details
                else None
            ),

            "acquisition_costs": [
                item.to_dict()
                for item in self.acquisition_costs.all()
            ],

            "renovations": [
                item.to_dict()
                for item in self.renovations.all()
            ],


            "maintenance": [
                item.to_dict()
                for item in self.maintenance.all()
            ],

            "insurance": [
                item.to_dict()
                for item in self.insurance.all()
            ],

            "furniture": [
                item.to_dict()
                for item in self.furniture.all()
            ],

            "valuation_history": [
                item.to_dict()
                for item in self.valuation_history.all()
            ],

            "sale": (
                sale.to_dict()
                if sale
                else None
            ),

            "purchase_payments": [
                item.to_dict()
                for item in purchase_payments
            ],

            "mortgage": (
                mortgage.to_dict()
                if mortgage
                else None
            ),

            "rental": (
                rental.to_dict()
                if rental
                else None
            ),

            "photos": [
                photo.to_dict()
                for photo in self.photos.all()
            ],
        }
