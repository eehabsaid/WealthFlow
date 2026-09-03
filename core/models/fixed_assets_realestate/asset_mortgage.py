from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.models.fixed_assets import FixedAsset
from core.models.fixed_assets_realestate.utils import _date_to_iso


class AssetMortgage(models.Model):
    asset = models.OneToOneField(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="mortgage",
    )

    loan_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    remaining_balance = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    monthly_installment = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    interest_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=0,
    )

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_dict(self):
        current_market_value = float(self.asset.current_market_value or 0)
        remaining_balance = float(self.remaining_balance or 0)
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "loan_amount": float(self.loan_amount or 0),
            "remaining_balance": remaining_balance,
            "monthly_installment": float(self.monthly_installment or 0),
            "interest_rate": float(self.interest_rate or 0),
            "start_date": _date_to_iso(self.start_date),
            "end_date": _date_to_iso(self.end_date),
            "net_equity": current_market_value - remaining_balance,
        }


@receiver(post_save, sender=AssetMortgage)
def handle_asset_mortgage_save(sender, instance, **kwargs):
    from core.services.balance.financial_sync_service import FinancialSyncService
    FinancialSyncService().sync_mortgage_balance(instance)


@receiver(post_delete, sender=AssetMortgage)
def handle_asset_mortgage_delete(sender, instance, **kwargs):
    from core.services.balance.financial_sync_service import FinancialSyncService
    FinancialSyncService().sync_deleted_mortgage_balance(instance)
