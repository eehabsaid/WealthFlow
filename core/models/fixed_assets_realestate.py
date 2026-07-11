from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from datetime import date, datetime
from .fixed_assets import FixedAsset

def _date_to_iso(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if value:
        return str(value)
    return ""


class RealEstateDetails(models.Model):
    asset = models.OneToOneField(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="real_estate",
    )

    country = models.CharField(max_length=100, default="Egypt")
    governorate = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    full_address = models.TextField(blank=True)

    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    area_m2 = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    bedrooms = models.PositiveSmallIntegerField(default=0)
    bathrooms = models.PositiveSmallIntegerField(default=0)

    floor_number = models.PositiveSmallIntegerField(default=0)
    building_floors = models.PositiveSmallIntegerField(default=0)

    build_year = models.PositiveSmallIntegerField(null=True, blank=True)

    has_elevator = models.BooleanField(default=False)
    has_garage = models.BooleanField(default=False)
    has_gas = models.BooleanField(default=False)

    electricity_meter_private = models.BooleanField(default=True)
    water_meter_private = models.BooleanField(default=False)

    has_land_share = models.BooleanField(default=False)
    land_share_ratio = models.CharField(max_length=50, blank=True)

    facing = models.CharField(max_length=100, blank=True)

    licensed = models.BooleanField(default=False)
    land_share_sqm = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True)

    finishing_level = models.CharField(max_length=100, blank=True)

    last_estimated_market_price = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
    )

    last_valuation_date = models.DateField(
        null=True,
        blank=True,
    )

    valuation_provider = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    furnished_status = models.CharField(
        max_length=50,
        choices=[
            ("Unfurnished", "Unfurnished"),
            ("Semi Furnished", "Semi Furnished"),
            ("Fully Furnished", "Fully Furnished"),
        ],
        default="Unfurnished",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_dict(self):
        return {
            "country": self.country,
            "governorate": self.governorate,
            "city": self.city,
            "district": self.district,
            "address": self.full_address,
            "rooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "floor": self.floor_number,
            "building_floors": self.building_floors,
            "building_year": self.build_year,
            "facades": self.facing,
            "finishing_level": self.finishing_level,
            "furnished_status": self.furnished_status,
            "electricity": self.electricity_meter_private,
            "water": self.water_meter_private,
            "gas": self.has_gas,
            "elevator": self.has_elevator,
            "garage": self.has_garage,
            "has_land_share":self.has_land_share,
            "land_share": self.land_share_ratio,
            "apartment_area": float(self.area_m2),
            "land_area": float(self.land_share_sqm),
            "latitude": float(self.latitude) if self.latitude else None,
            "longitude": float(self.longitude) if self.longitude else None,
            "licensed": self.licensed,
            "description": self.description,
            "last_estimated_market_price": float(self.last_estimated_market_price) if self.last_estimated_market_price is not None else None,
            "last_valuation_date": self.last_valuation_date.isoformat() if self.last_valuation_date else "",
            "valuation_provider": self.valuation_provider,
        }

    def __str__(self):
        return f"{self.asset.name} Details"


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


class AssetRental(models.Model):
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
