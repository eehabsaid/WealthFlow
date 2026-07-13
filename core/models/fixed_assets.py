from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from decimal import Decimal

from core.constants import ASSET_TYPES, ASSET_STATUS, VALUATION_SOURCE

class FixedAsset(models.Model):
    name = models.CharField(max_length=200)

    asset_type = models.CharField(
        max_length=30,
        choices=ASSET_TYPES,
    )

    status = models.CharField(
        max_length=20,
        choices=ASSET_STATUS,
        default="Owned",
    )

    purchase_date = models.DateField()

    purchase_price = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    purchase_usd_rate = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
    )

    purchase_price_usd = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    current_market_value = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    valuation_source = models.CharField(
        max_length=20,
        choices=VALUATION_SOURCE,
        default="Manual",
    )

    last_valuation_date = models.DateField(
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]

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
    def save(self, *args, **kwargs):
        if self.purchase_usd_rate and self.purchase_usd_rate > 0:
            self.purchase_price_usd = (
                Decimal(self.purchase_price) /
                Decimal(self.purchase_usd_rate)
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
