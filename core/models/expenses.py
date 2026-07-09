from django.db import models
from .currency import Currency
from .bank import Bank

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=10, default="💰")
    color_hex = models.CharField(max_length=7, default="#0d6efd")
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "name"]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "color_hex": self.color_hex,
            "order": self.order,
        }

    def __str__(self):
        return self.name


class ExpenseSubcategory(models.Model):
    category = models.ForeignKey(
        ExpenseCategory, on_delete=models.CASCADE, related_name="subcategories"
    )
    name = models.CharField(max_length=100)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "name"]
        unique_together = ["category", "name"]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category_id": self.category_id,
            "category_name": self.category.name,
            "category_icon": self.category.icon,
            "category_color": self.category.color_hex,
            "order": self.order,
        }

    def __str__(self):
        return f"{self.category.name} / {self.name}"


class Expense(models.Model):
    date = models.DateField()
    year = models.IntegerField()
    month = models.IntegerField()  # 1-12
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )
    subcategory = models.ForeignKey(
        ExpenseSubcategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )
    description = models.CharField(max_length=300, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.ForeignKey(
        Currency, on_delete=models.SET_NULL, null=True, blank=True
    )
    bank = models.ForeignKey(
        Bank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ("Cash", "Cash"),
            ("Card", "Card"),
            ("Bank Transfer", "Bank Transfer"),
            ("Other", "Other"),
        ],
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else "",
            "year": self.year,
            "month": self.month,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "",
            "category_icon": self.category.icon if self.category else "💰",
            "category_color": self.category.color_hex if self.category else "#0d6efd",
            "subcategory_id": self.subcategory_id,
            "subcategory_name": self.subcategory.name if self.subcategory else "",
            "description": self.description,
            "amount": float(self.amount),
            "currency_code": self.currency.code if self.currency else "EGP",
            "currency_symbol": self.currency.symbol if self.currency else "ج.م",
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "payment_method": self.payment_method,
            "notes": self.notes,
        }

    def __str__(self):
        return f"{self.date} {self.category} {self.amount}"
