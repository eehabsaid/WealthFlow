from django.db import models

class Bank(models.Model):
    name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=100, blank=True)
    card_id = models.CharField(max_length=100, blank=True)
    swift_code = models.CharField(max_length=50, blank=True)
    customer_id = models.CharField(max_length=100, blank=True)
    customer_name = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "account_number": self.account_number,
            "card_id": self.card_id,
            "swift_code": self.swift_code,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "is_active": self.is_active,
            "order": self.order,
        }

    def __str__(self):
        return self.name
