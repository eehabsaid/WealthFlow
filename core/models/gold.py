from django.db import models

class GoldTypeSetting(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "is_active": self.is_active,
            "order": self.order,
        }


class GoldPuritySetting(models.Model):
    key = models.CharField(max_length=20, unique=True)  # canonical: 24k, 22k, ...
    label = models.CharField(max_length=50)
    cashback_per_gram = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "key"]

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "label": self.label,
            "cashback_per_gram": float(self.cashback_per_gram or 0),
            "is_active": self.is_active,
            "order": self.order,
        }


class GoldPrice(models.Model):
    """One row per fetch. Stores EGP price per gram for common carats."""

    # Sell prices (EGP per gram)
    carat_24k = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    carat_22k = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    carat_21k = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    carat_18k = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Buy prices (EGP per gram)
    carat_24k_buy = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    carat_22k_buy = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    carat_21k_buy = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    carat_18k_buy = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Raw USD per gram values stored so user can see them too
    usd_gram_24k = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    usd_per_oz = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    usd_to_egp = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    source_gold = models.CharField(max_length=100, default="api.gold-api.com")
    source_fx = models.CharField(max_length=100, default="open.er-api.com")
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fetched_at"]

    def to_dict(self):
        return {
            "id": self.id,
            "carat_24k": float(self.carat_24k),
            "carat_22k": float(self.carat_22k),
            "carat_21k": float(self.carat_21k),
            "carat_18k": float(self.carat_18k),
            "carat_24k_buy": float(self.carat_24k_buy),
            "carat_22k_buy": float(self.carat_22k_buy),
            "carat_21k_buy": float(self.carat_21k_buy),
            "carat_18k_buy": float(self.carat_18k_buy),
            "usd_gram_24k": float(self.usd_gram_24k),
            "usd_per_oz": float(self.usd_per_oz),
            "usd_to_egp": float(self.usd_to_egp),
            "source_gold": self.source_gold,
            "source_fx": self.source_fx,
            "fetched_at": (
                self.fetched_at.strftime("%Y-%m-%d %H:%M") if self.fetched_at else ""
            ),
        }

    def __str__(self):
        return f"Gold {self.fetched_at}  21K={self.carat_21k} EGP/g"


class GoldPriceHistory(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    carat_24k = models.DecimalField(max_digits=12, decimal_places=2)
    carat_21k = models.DecimalField(max_digits=12, decimal_places=2)
    carat_18k = models.DecimalField(max_digits=12, decimal_places=2)
    usd_gram_24k = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    usd_per_oz = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    usd_to_egp = models.DecimalField(max_digits=10, decimal_places=6, default=0)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M}"
