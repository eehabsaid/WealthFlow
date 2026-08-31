"""AssetSale model and its pre_save/post_save/post_delete signal handlers.

NOTE: Split out of the former core/models/fixed_assets_history.py (562
lines) per the 200-line file split rule. One model per file; see
core/models/fixed_assets_history/__init__.py for the package convention.
"""
from decimal import Decimal

from django.db import models
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from core.models.fixed_assets import FixedAsset
from core.models.currency import Currency
from core.models.bank import Bank
from core.models.balance import BalanceEntry


class AssetSale(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("Cash", "Cash"),
        ("Card", "Card"),
        ("Bank", "Bank"),
        ("Bank Transfer", "Bank Transfer"),
    ]

    asset = models.OneToOneField(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="sale",
    )

    sale_date = models.DateField()

    sale_price = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    selling_expenses = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    net_sale_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    deposit_balance = models.ForeignKey(
        BalanceEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_sales",
    )

    deposit_currency = models.ForeignKey(
        Currency,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_sales_deposits",
    )

    deposit_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
        default="Cash",
    )

    deposit_bank = models.ForeignKey(
        Bank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_sales_deposits",
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def to_dict(self):
        currency = self.deposit_currency
        if currency is None:
            currency = Currency.objects.filter(code__iexact="EGP").order_by("id").first()

        method = str(self.deposit_method or "").strip() or "Cash"
        if method.lower() == "cash":
            bank_id = None
            bank_name = ""
        else:
            bank_id = self.deposit_bank_id
            bank_name = self.deposit_bank.name if self.deposit_bank else ""

        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "sale_date": (
                self.sale_date.isoformat()
                if self.sale_date
                else ""
            ),
            "sale_price": float(self.sale_price),
            "selling_expenses": float(self.selling_expenses),
            "net_sale_amount": float(self.net_sale_amount),
            "deposit_balance_id": self.deposit_balance_id,
            "deposit_currency_id": currency.id if currency else None,
            "deposit_currency_code": currency.code if currency else "",
            "deposit_method": method,
            "deposit_bank_id": bank_id,
            "deposit_bank_name": bank_name,
            "notes": self.notes,
        }

    def __str__(self):
        return f"{self.asset.name} Sold"


@receiver(pre_save, sender=AssetSale)
def handle_asset_sale_pre_save(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_deposit_balance_id = None
        instance._previous_net_sale_amount = Decimal("0")
        return

    previous = AssetSale.objects.filter(pk=instance.pk).first()
    instance._previous_deposit_balance_id = previous.deposit_balance_id if previous else None
    instance._previous_net_sale_amount = previous.net_sale_amount if previous else Decimal("0")


@receiver(post_save, sender=AssetSale)
def handle_asset_sale_save(sender, instance, created, **kwargs):
    from core.services.balance.financial_sync_service import FinancialSyncService
    FinancialSyncService().sync_asset_sale_balance(instance)


@receiver(post_delete, sender=AssetSale)
def handle_asset_sale_delete(sender, instance, **kwargs):
    from core.services.balance.financial_sync_service import FinancialSyncService
    FinancialSyncService().sync_deleted_asset_sale_balance(instance)
