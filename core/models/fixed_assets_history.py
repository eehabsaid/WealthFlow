from django.db import models
from decimal import Decimal
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from .fixed_assets import FixedAsset, VALUATION_SOURCE
from .currency import Currency
from .bank import Bank
from .balance import BalanceEntry

class AssetRenovation(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("Cash", "Cash"),
        ("Card", "Card"),
        ("Bank", "Bank"),
        ("Bank Transfer", "Bank Transfer"),
    ]

    asset = models.ForeignKey(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="renovations",
    )

    furniture = models.ForeignKey(
        "AssetFurniture",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="renovations",
    )

    date = models.DateField()

    category = models.CharField(
        max_length=100,
    )

    description = models.CharField(
        max_length=300,
        blank=True,
    )

    amount_egp = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    usd_rate = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
    )

    amount_usd = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
        default="Cash",
    )

    bank = models.ForeignKey(
        Bank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_renovations",
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-date", "-id"]

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "furniture_id": self.furniture_id,
            "furniture_name": self.furniture.name if self.furniture else "",
            "date": self.date.isoformat() if hasattr(self.date, "isoformat") else (self.date or ""),
            "category": self.category,
            "description": self.description,
            "amount_egp": float(self.amount_egp),
            "usd_rate": float(self.usd_rate),
            "amount_usd": float(self.amount_usd),
            "payment_method": self.payment_method,
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "notes": self.notes,
        }
    
    def __str__(self):
        return f"{self.asset.name} - {self.category}"


@receiver(post_save, sender=AssetRenovation)
def handle_asset_renovation_save(sender, instance, **kwargs):
    from core.services.fixed_assets.asset_expense_mirror_service import sync_renovation_mirror
    sync_renovation_mirror(instance)


@receiver(post_delete, sender=AssetRenovation)
def handle_asset_renovation_delete(sender, instance, **kwargs):
    from core.services.fixed_assets.asset_expense_mirror_service import delete_renovation_mirror
    delete_renovation_mirror(instance.id)


class AssetFurniture(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("Cash", "Cash"),
        ("Card", "Card"),
        ("Bank", "Bank"),
        ("Bank Transfer", "Bank Transfer"),
    ]

    asset = models.ForeignKey(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="furniture",
    )

    name = models.CharField(max_length=200)

    category = models.CharField(
        max_length=100,
        blank=True,
    )

    purchase_date = models.DateField(
        null=True,
        blank=True,
    )

    amount_egp = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    usd_rate = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
    )

    amount_usd = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    quantity = models.PositiveIntegerField(default=1)

    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
        default="Cash",
    )

    bank = models.ForeignKey(
        Bank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_furniture",
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
    
    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "name": self.name,
            "category": self.category,
            "purchase_date": (
                self.purchase_date.isoformat()
                if hasattr(self.purchase_date, "isoformat")
                else (self.purchase_date or "")
            ),
            "amount_egp": float(self.amount_egp),
            "usd_rate": float(self.usd_rate),
            "amount_usd": float(self.amount_usd),
            "quantity": self.quantity,
            "payment_method": self.payment_method,
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "notes": self.notes,
        }

    def __str__(self):
        return f"{self.asset.name} - {self.name}"


@receiver(post_save, sender=AssetFurniture)
def handle_asset_furniture_save(sender, instance, **kwargs):
    from core.services.fixed_assets.asset_expense_mirror_service import sync_furniture_mirror
    sync_furniture_mirror(instance)


@receiver(post_delete, sender=AssetFurniture)
def handle_asset_furniture_delete(sender, instance, **kwargs):
    from core.services.fixed_assets.asset_expense_mirror_service import delete_furniture_mirror
    delete_furniture_mirror(instance.id)


class AssetValuationHistory(models.Model):
    asset = models.ForeignKey(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="valuation_history",
    )

    valuation_date = models.DateField()

    market_value = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    valuation_source = models.CharField(
        max_length=20,
        choices=VALUATION_SOURCE,
        default="Manual",
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-valuation_date", "-id"]

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "valuation_date": (
                self.valuation_date.isoformat()
                if self.valuation_date
                else ""
            ),
            "market_value": float(self.market_value),
            "valuation_source": self.valuation_source,
            "notes": self.notes,
        }

    def __str__(self):
        return f"{self.asset.name} - {self.valuation_date}"


class AssetPurchasePayment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("Cash", "Cash"),
        ("Card", "Card"),
        ("Bank", "Bank"),
        ("Bank Transfer", "Bank Transfer"),
    ]

    asset = models.ForeignKey(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="purchase_payments",
    )

    currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name="asset_purchase_payments",
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
        default="Cash",
    )

    bank = models.ForeignKey(
        Bank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_purchase_payments",
    )

    amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "currency_id": self.currency_id,
            "currency_code": self.currency.code if self.currency else "",
            "payment_method": self.payment_method,
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "amount": float(self.amount),
        }

    def __str__(self):
        return f"{self.asset.name} payment {self.amount}"


class AssetSale(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("Cash", "Cash"),
        ("Card", "Card"),
        ("Bank", "Bank"),
        ("Bank Transfer", "Bank Transfer"),
    ]

    asset = models.OneToOneField(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="sale",
    )

    sale_date = models.DateField()

    sale_price = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    selling_expenses = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    net_sale_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    deposit_balance = models.ForeignKey(
        BalanceEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_sales",
    )

    deposit_currency = models.ForeignKey(
        Currency,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_sales_deposits",
    )

    deposit_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
        default="Cash",
    )

    deposit_bank = models.ForeignKey(
        Bank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_sales_deposits",
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def to_dict(self):
        currency = self.deposit_currency
        if currency is None:
            currency = Currency.objects.filter(code__iexact="EGP").order_by("id").first()

        method = str(self.deposit_method or "").strip() or "Cash"
        if method.lower() == "cash":
            bank_id = None
            bank_name = ""
        else:
            bank_id = self.deposit_bank_id
            bank_name = self.deposit_bank.name if self.deposit_bank else ""

        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "sale_date": (
                self.sale_date.isoformat()
                if self.sale_date
                else ""
            ),
            "sale_price": float(self.sale_price),
            "selling_expenses": float(self.selling_expenses),
            "net_sale_amount": float(self.net_sale_amount),
            "deposit_balance_id": self.deposit_balance_id,
            "deposit_currency_id": currency.id if currency else None,
            "deposit_currency_code": currency.code if currency else "",
            "deposit_method": method,
            "deposit_bank_id": bank_id,
            "deposit_bank_name": bank_name,
            "notes": self.notes,
        }

    def __str__(self):
        return f"{self.asset.name} Sold"


@receiver(pre_save, sender=AssetSale)
def handle_asset_sale_pre_save(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_deposit_balance_id = None
        instance._previous_net_sale_amount = Decimal("0")
        return

    previous = AssetSale.objects.filter(pk=instance.pk).first()
    instance._previous_deposit_balance_id = previous.deposit_balance_id if previous else None
    instance._previous_net_sale_amount = previous.net_sale_amount if previous else Decimal("0")


@receiver(post_save, sender=AssetSale)
def handle_asset_sale_save(sender, instance, created, **kwargs):
    from core.services.balance.financial_sync_service import FinancialSyncService
    FinancialSyncService().sync_asset_sale_balance(instance)


@receiver(post_delete, sender=AssetSale)
def handle_asset_sale_delete(sender, instance, **kwargs):
    from core.services.balance.financial_sync_service import FinancialSyncService
    FinancialSyncService().sync_deleted_asset_sale_balance(instance)


class AssetAcquisitionCost(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("Cash", "Cash"),
        ("Card", "Card"),
        ("Bank", "Bank"),
        ("Bank Transfer", "Bank Transfer"),
    ]

    asset = models.ForeignKey(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="acquisition_costs",
    )

    date = models.DateField(null=True, blank=True)

    category = models.CharField(
        max_length=100,
    )

    description = models.CharField(
        max_length=300,
        blank=True,
    )

    amount_egp = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    usd_rate = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
    )

    amount_usd = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
        default="Cash",
    )

    bank = models.ForeignKey(
        Bank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_acquisition_costs",
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["date", "id"]

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "date": self.date.isoformat() if hasattr(self.date, "isoformat") else (self.date or ""),
            "category": self.category,
            "description": self.description,
            "amount_egp": float(self.amount_egp),
            "usd_rate": float(self.usd_rate),
            "amount_usd": float(self.amount_usd),
            "payment_method": self.payment_method,
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "notes": self.notes,
        }

    def __str__(self):
        return f"{self.asset.name} - {self.category}"


@receiver(post_save, sender=AssetAcquisitionCost)
def handle_asset_acquisition_cost_save(sender, instance, **kwargs):
    from core.services.fixed_assets.asset_expense_mirror_service import sync_acquisition_cost_mirror
    sync_acquisition_cost_mirror(instance)


@receiver(post_delete, sender=AssetAcquisitionCost)
def handle_asset_acquisition_cost_delete(sender, instance, **kwargs):
    from core.services.fixed_assets.asset_expense_mirror_service import delete_acquisition_cost_mirror
    delete_acquisition_cost_mirror(instance.id)
