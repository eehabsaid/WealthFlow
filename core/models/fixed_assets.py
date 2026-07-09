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
