"""AssetValuationHistory model.

NOTE: Split out of the former core/models/fixed_assets_history.py (562
lines) per the 200-line file split rule. One model per file; see
core/models/fixed_assets_history/__init__.py for the package convention.
"""
from django.db import models

from core.models.fixed_assets import FixedAsset, VALUATION_SOURCE


class AssetValuationHistory(models.Model):
    asset = models.ForeignKey(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="valuation_history",
    )

    valuation_date = models.DateField()

    market_value = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    valuation_source = models.CharField(
        max_length=20,
        choices=VALUATION_SOURCE,
        default="Manual",
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-valuation_date", "-id"]

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "valuation_date": (
                self.valuation_date.isoformat()
                if self.valuation_date
                else ""
            ),
            "market_value": float(self.market_value),
            "valuation_source": self.valuation_source,
            "notes": self.notes,
        }

    def __str__(self):
        return f"{self.asset.name} - {self.valuation_date}"
