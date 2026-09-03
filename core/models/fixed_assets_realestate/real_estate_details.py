from django.db import models

from core.models.fixed_assets import FixedAsset


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
