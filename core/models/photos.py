from django.db import models
from .fixed_assets import FixedAsset

class AssetPhoto(models.Model):
    asset = models.ForeignKey(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="photos",
    )

    image_data = models.BinaryField(
        null=True,
        blank=True
    )
    filename = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
    mime_type = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    title = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-uploaded_at"]

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "filename": self.filename,
            "url": f"/api/fixed-assets/photo/{self.id}/",
        }

    def __str__(self):
        return self.title or f"Photo #{self.id}"
