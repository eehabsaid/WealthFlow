from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.models.fixed_assets import FixedAsset
from core.models.fixed_assets_realestate.utils import _date_to_iso


class AssetRental(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("Cash", "Cash"),
        ("Card", "Card"),
        ("Bank", "Bank"),
        ("Bank Transfer", "Bank Transfer"),
    ]

    asset = models.OneToOneField(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="rental",
    )

    monthly_rent = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    occupancy_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    tenant_name = models.CharField(max_length=200, blank=True)
    contract_start = models.DateField(null=True, blank=True)
    contract_end = models.DateField(null=True, blank=True)

    receive_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
        default="Cash",
    )

    bank = models.ForeignKey(
        "Bank",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_rentals",
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_dict(self):
        monthly_rent = float(self.monthly_rent or 0)
        annual_rent = monthly_rent * 12
        current_market_value = float(self.asset.current_market_value or 0)
        rental_yield = (annual_rent / current_market_value * 100) if current_market_value > 0 else 0
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "monthly_rent": monthly_rent,
            "annual_rent": annual_rent,
            "occupancy_rate": float(self.occupancy_rate or 0),
            "rental_yield": rental_yield,
            "tenant_name": self.tenant_name,
            "contract_start": _date_to_iso(self.contract_start),
            "contract_end": _date_to_iso(self.contract_end),
            "receive_method": self.receive_method,
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "notes": self.notes,
        }


@receiver(post_save, sender=AssetRental)
def handle_asset_rental_save(sender, instance, **kwargs):
    from core.services.balance.financial_sync_service import FinancialSyncService
    FinancialSyncService().sync_rental_balance(instance)


@receiver(post_delete, sender=AssetRental)
def handle_asset_rental_delete(sender, instance, **kwargs):
    from core.services.balance.financial_sync_service import FinancialSyncService
    FinancialSyncService().sync_deleted_rental_balance(instance)
