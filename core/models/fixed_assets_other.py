from django.db import models
from .fixed_assets import FixedAsset

class OtherAssetDetails(models.Model):
    asset = models.OneToOneField(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="other_asset_details",
    )
    category = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            "category": self.category,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "serial_number": self.serial_number,
            "description": self.description,
            "warranty_expiry": self.warranty_expiry.isoformat() if self.warranty_expiry else "",
            "notes": self.notes,
        }
