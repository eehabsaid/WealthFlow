from django.db import models


class ExchangeRateHistory(models.Model):
    """
    Analytical-only archive of exchange rate snapshots.

    One row per (currency_code, snapshot_date).
    snapshot_date is derived from the original fetched_at timestamp
    in core_exchangerate — never from the system clock at archive time.

    This table is the single source of truth for all historical
    exchange-rate queries (financial advisor, portfolio optimizer,
    forecasting, reports, analytics).  All access must go through
    ExchangeRateHistoryService — never query this model directly
    from views or other services.
    """

    currency_code = models.CharField(max_length=10)
    currency_name = models.CharField(max_length=100, blank=True)

    # All rates stored as Decimal — never converted to float internally.
    buy_rate = models.DecimalField(max_digits=14, decimal_places=6, default=0)
    sell_rate = models.DecimalField(max_digits=14, decimal_places=6, default=0)
    mid_rate = models.DecimalField(max_digits=14, decimal_places=6, default=0)

    source = models.CharField(max_length=100, default="open.er-api.com")

    # Preserved from the original ExchangeRate.fetched_at value.
    fetched_at = models.DateTimeField()

    # Recorded when this row was inserted into the history table.
    archived_at = models.DateTimeField(auto_now_add=True)

    # Date portion of fetched_at; used as the unique key per currency per day.
    snapshot_date = models.DateField()

    class Meta:
        unique_together = [("currency_code", "snapshot_date")]
        indexes = [
            models.Index(fields=["currency_code", "snapshot_date"]),
        ]
        ordering = ["-snapshot_date", "currency_code"]

    def to_dict(self):
        return {
            "id": self.id,
            "currency_code": self.currency_code,
            "currency_name": self.currency_name,
            # Return strings to preserve Decimal precision for callers.
            "buy_rate": str(self.buy_rate),
            "sell_rate": str(self.sell_rate),
            "mid_rate": str(self.mid_rate),
            "source": self.source,
            "fetched_at": (
                self.fetched_at.strftime("%Y-%m-%d %H:%M") if self.fetched_at else ""
            ),
            "archived_at": (
                self.archived_at.strftime("%Y-%m-%d %H:%M") if self.archived_at else ""
            ),
            "snapshot_date": str(self.snapshot_date) if self.snapshot_date else "",
        }

    def __str__(self):
        return f"{self.currency_code} {self.snapshot_date}  mid={self.mid_rate}"
