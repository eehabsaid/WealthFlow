"""AssetPurchasePayment model.

NOTE: Split out of the former core/models/fixed_assets_history.py (562
lines) per the 200-line file split rule. One model per file; see
core/models/fixed_assets_history/__init__.py for the package convention.
"""
from django.db import models

from core.models.fixed_assets import FixedAsset
from core.models.currency import Currency
from core.models.bank import Bank


class AssetPurchasePayment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("Cash", "Cash"),
        ("Card", "Card"),
        ("Bank", "Bank"),
        ("Bank Transfer", "Bank Transfer"),
    ]

    asset = models.ForeignKey(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="purchase_payments",
    )

    currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name="asset_purchase_payments",
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
        related_name="asset_purchase_payments",
    )

    amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "currency_id": self.currency_id,
            "currency_code": self.currency.code if self.currency else "",
            "payment_method": self.payment_method,
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "amount": float(self.amount),
        }

    def __str__(self):
        return f"{self.asset.name} payment {self.amount}"
