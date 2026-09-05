from django.db import models


class CertificateStatus(models.Model):
    """Admin-configurable certificate lifecycle statuses."""

    name = models.CharField(max_length=100, unique=True)
    color_hex = models.CharField(max_length=7, default="#1a6ef5")
    is_default = models.BooleanField(
        default=False, help_text="Used as default status for new certs"
    )
    is_terminal = models.BooleanField(
        default=False, help_text="No further renewals expected"
    )
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "color_hex": self.color_hex,
            "is_default": self.is_default,
            "is_terminal": self.is_terminal,
            "order": self.order,
        }

    def __str__(self):
        return self.name
