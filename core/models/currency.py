from django.db import models

class Currency(models.Model):
    code = models.CharField(max_length=10, unique=True)  # USD, EGP, SAR
    symbol = models.CharField(max_length=10, default="")  # $, ج.م, ﷼
    flag = models.CharField(max_length=10, default="💱")  # 🇺🇸, 🇪🇬, 🇸🇦
    name = models.CharField(max_length=100)  # US Dollar, Egyptian Pound
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "code"]

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
