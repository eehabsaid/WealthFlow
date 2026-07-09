from django.db import models

class ExchangeRate(models.Model):
    """One row per currency per fetch. Latest row = current rate."""

    currency_code = models.CharField(max_length=10)  # USD, EUR, SAR …
    currency_name = models.CharField(max_length=100, blank=True)
    buy_rate = models.DecimalField(max_digits=14, decimal_places=6, default=0)
    sell_rate = models.DecimalField(max_digits=14, decimal_places=6, default=0)
    mid_rate = models.DecimalField(max_digits=14, decimal_places=6, default=0)
    source = models.CharField(max_length=50, default="open.er-api.com")
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fetched_at", "currency_code"]

    def to_dict(self):
        return {
            "id": self.id,
            "currency_code": self.currency_code,
            "currency_name": self.currency_name,
            "buy_rate": float(self.buy_rate),
            "sell_rate": float(self.sell_rate),
            "mid_rate": float(self.mid_rate),
            "source": self.source,
            "fetched_at": (
                self.fetched_at.strftime("%Y-%m-%d %H:%M") if self.fetched_at else ""
            ),
        }

    def __str__(self):
        return f"{self.currency_code} → EGP  mid={self.mid_rate}"
