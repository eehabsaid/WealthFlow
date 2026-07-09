from django.db import models
from datetime import date, datetime

def _date_to_iso(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if value:
        return str(value)
    return ""


class Goal(models.Model):
    PRIORITY_CHOICES = [
        ("High", "High"),
        ("Medium", "Medium"),
        ("Low", "Low"),
    ]

    name = models.CharField(max_length=200)
    goal_type = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    currency = models.ForeignKey("Currency", on_delete=models.SET_NULL, null=True, blank=True)
    target_date = models.DateField(null=True, blank=True)
    current_saved_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    linked_asset = models.ForeignKey(
        "FixedAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_goals",
    )
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="Medium")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["target_date", "id"]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "goal_type": self.goal_type,
            "target_amount": float(self.target_amount or 0),
            "currency_id": self.currency_id,
            "currency_code": self.currency.code if self.currency else "EGP",
            "currency_symbol": self.currency.symbol if self.currency else "",
            "target_date": _date_to_iso(self.target_date),
            "current_saved_amount": float(self.current_saved_amount or 0),
            "linked_asset_id": self.linked_asset_id,
            "linked_asset_name": self.linked_asset.name if self.linked_asset else "",
            "priority": self.priority,
            "notes": self.notes,
        }
