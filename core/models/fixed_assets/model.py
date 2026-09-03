from decimal import Decimal

from django.db import models

from core.constants import ASSET_STATUS, ASSET_TYPES, VALUATION_SOURCE
from core.models.fixed_assets.calculations_mixin import FixedAssetCalculationsMixin
from core.models.fixed_assets.serialization_mixin import FixedAssetSerializationMixin


class FixedAsset(FixedAssetCalculationsMixin, FixedAssetSerializationMixin, models.Model):
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

    def save(self, *args, **kwargs):
        if self.purchase_usd_rate and self.purchase_usd_rate > 0:
            self.purchase_price_usd = (
                Decimal(self.purchase_price) /
                Decimal(self.purchase_usd_rate)
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
