from django.db import models
from django.conf import settings


class Currency(models.Model):
    """Per-user currency catalog. owner=NULL rows are the internal
    platform template — never shown to any user, cloned into every
    new/existing user's own copy (see 00xx_per_user_catalogs migration
    and the signup seeding hook)."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="currencies",
    )
    code = models.CharField(max_length=10)  # USD, EGP, SAR
    symbol = models.CharField(max_length=10, default="")  # $, ج.م, ﷼
    flag = models.CharField(max_length=10, default="💱")  # 🇺🇸, 🇪🇬, 🇸🇦
    name = models.CharField(max_length=100)  # US Dollar, Egyptian Pound
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "code"]
        unique_together = ["owner", "code"]

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "symbol": self.symbol,
            "flag": self.flag,
            "name": self.name,
            "order": self.order,
        }

    def __str__(self):
        return f"{self.code} - {self.name}"
