from django.db import models
from django.conf import settings


class CertificateStatus(models.Model):
    """Per-user certificate lifecycle status catalog. owner=NULL rows are
    the internal platform template — see Currency model docstring for the
    pattern."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="certificate_statuses",
    )
    name = models.CharField(max_length=100)
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
        unique_together = ["owner", "name"]

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
