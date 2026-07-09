from django.db import models
from .fixed_assets import FixedAsset

class GoldDetails(models.Model):
    asset = models.OneToOneField(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="gold_details",
    )
    gold_type = models.CharField(max_length=100, blank=True)
    purity = models.CharField(max_length=50, blank=True)
    weight = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    unit = models.CharField(max_length=20, default="gram")
    market_price = models.DecimalField(max_digits=16, decimal_places=4, default=0)
    cashback_per_gram = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    purchase_weight = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def to_dict(self):
        weight = float(self.weight or 0)
        market_price = float(self.market_price or 0)
        cashback_per_gram = float(self.cashback_per_gram or 0)
        purchase_weight = float(self.purchase_weight or 0)
        normalized_unit = (self.unit or "gram").strip().lower()

        unit_to_gram = {
            "g": 1.0,
            "gm": 1.0,
            "gram": 1.0,
            "grams": 1.0,
            "kg": 1000.0,
            "kilogram": 1000.0,
            "kilograms": 1000.0,
            "oz": 31.1034768,
            "ounce": 31.1034768,
            "ounces": 31.1034768,
            "tola": 11.6638038,
        }
        grams_per_unit = unit_to_gram.get(normalized_unit, 1.0)
        weight_in_grams = weight * grams_per_unit
        sell_price_per_gram = market_price / grams_per_unit if grams_per_unit > 0 else market_price
        effective_sell_price_per_gram = sell_price_per_gram + cashback_per_gram
        current_valuation = weight_in_grams * effective_sell_price_per_gram

        return {
            "gold_type": self.gold_type,
            "purity": self.purity,
            "weight": weight,
            "unit": self.unit,
            "market_price": market_price,
            "cashback_per_gram": cashback_per_gram,
            "purchase_weight": purchase_weight,
            "weight_in_grams": weight_in_grams,
            "sell_price_per_gram": sell_price_per_gram,
            "effective_sell_price_per_gram": effective_sell_price_per_gram,
            "current_valuation": current_valuation,
        }
