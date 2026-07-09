from django.db import models
from .fixed_assets import FixedAsset

class VehicleDetails(models.Model):
    asset = models.OneToOneField(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="vehicle_details",
    )
    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    vin = models.CharField(max_length=100, blank=True)
    engine = models.CharField(max_length=100, blank=True)
    transmission = models.CharField(max_length=100, blank=True)
    fuel_type = models.CharField(max_length=50, blank=True)
    mileage = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    plate_number = models.CharField(max_length=100, blank=True)
    license_expiry_date = models.DateField(null=True, blank=True)
    color = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            "brand": self.brand,
            "model": self.model,
            "year": self.year,
            "vin": self.vin,
            "engine": self.engine,
            "transmission": self.transmission,
            "fuel_type": self.fuel_type,
            "mileage": float(self.mileage or 0),
            "plate_number": self.plate_number,
            "license_expiry_date": self.license_expiry_date.isoformat() if self.license_expiry_date else "",
            "color": self.color,
        }


class AssetMaintenance(models.Model):
    asset = models.ForeignKey(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="maintenance",
    )
    date = models.DateField()
    maintenance_type = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "id"]

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "date": self.date.isoformat() if self.date else "",
            "type": self.maintenance_type,
            "cost": float(self.cost or 0),
            "notes": self.notes,
        }


class AssetInsurance(models.Model):
    asset = models.ForeignKey(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="insurance",
    )
    company = models.CharField(max_length=200)
    policy_number = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    premium = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["expiry_date", "id"]

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "company": self.company,
            "policy_number": self.policy_number,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else "",
            "premium": float(self.premium or 0),
        }
