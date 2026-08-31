"""AssetAcquisitionCost model and its post_save/post_delete signal handlers.

NOTE: Split out of the former core/models/fixed_assets_history.py (562
lines) per the 200-line file split rule. One model per file; see
core/models/fixed_assets_history/__init__.py for the package convention.
"""
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from core.models.fixed_assets import FixedAsset
from core.models.bank import Bank


class AssetAcquisitionCost(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("Cash", "Cash"),
        ("Card", "Card"),
        ("Bank", "Bank"),
        ("Bank Transfer", "Bank Transfer"),
    ]

    asset = models.ForeignKey(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="acquisition_costs",
    )

    date = models.DateField(null=True, blank=True)

    category = models.CharField(
        max_length=100,
    )

    description = models.CharField(
        max_length=300,
        blank=True,
    )

    amount_egp = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    usd_rate = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
    )

    amount_usd = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
        default="Cash",
    )

    bank = models.ForeignKey(
        Bank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_acquisition_costs",
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
        ordering = ["-date", "-id"]

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "date": self.date.isoformat() if hasattr(self.date, "isoformat") else (self.date or ""),
            "category": self.category,
            "description": self.description,
            "amount_egp": float(self.amount_egp),
            "usd_rate": float(self.usd_rate),
            "amount_usd": float(self.amount_usd),
            "payment_method": self.payment_method,
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "notes": self.notes,
        }

    def __str__(self):
        return f"{self.asset.name} - {self.category}"


@receiver(post_save, sender=AssetAcquisitionCost)
def handle_asset_acquisition_cost_save(sender, instance, **kwargs):
    from core.services.fixed_assets.asset_expense_mirror_service import sync_acquisition_cost_mirror
    sync_acquisition_cost_mirror(instance)


@receiver(post_delete, sender=AssetAcquisitionCost)
def handle_asset_acquisition_cost_delete(sender, instance, **kwargs):
    from core.services.fixed_assets.asset_expense_mirror_service import delete_acquisition_cost_mirror
    delete_acquisition_cost_mirror(instance.id)
