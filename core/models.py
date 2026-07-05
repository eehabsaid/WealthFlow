from datetime import date, datetime

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from decimal import Decimal
from django.db.models import Case, Value, When

ASSET_TYPES = [
    ("Real Estate", "Real Estate"),
    ("Vehicles", "Vehicles"),
    ("Gold", "Gold"),
    ("Other Assets", "Other Assets"),
]

ASSET_STATUS = [
    ("Owned", "Owned"),
    ("Sold", "Sold"),
]

VALUATION_SOURCE = [
    ("Manual", "Manual"),
    ("Automatic", "Automatic"),
]

PAGE_PERMISSION_CHOICES = [
    ("dashboard", "Dashboard"),
    ("companies", "Companies"),
    ("salary", "Salary"),
    ("all_companies", "All Companies"),
    ("banks", "Banks"),
    ("bank_certificates", "Bank Certificates"),
    ("currencies", "Currencies"),
    ("balance", "Balance"),
    ("settings", "Settings"),
    ("expense-categories", "Expense Categories"),
    ("exchange_rates", "Exchange Rates"),
    ("gold_price", "Gold Price"),
    ("user_management", "User Management"),
    ("expenses", "Expenses"),
    ("reports", "Reports"),
    ("fixed_assets", "Fixed Assets"),
    ("advanced_reports", "Advanced Reports"),
]


class Company(models.Model):
    name = models.CharField(max_length=200, unique=True)
    display_name = models.CharField(max_length=200)
    group_name = models.CharField(max_length=200, blank=True)
    color_hex = models.CharField(max_length=7, default="#0d6efd")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "name"]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "group_name": self.group_name,
            "color_hex": self.color_hex,
            "is_active": self.is_active,
            "order": self.order,
        }

    def __str__(self):
        return self.name


class SalaryEntry(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="salary_entries"
    )
    year = models.IntegerField()
    month = models.CharField(max_length=50)
    expected = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["year", "month"]
        unique_together = ["company", "year", "month"]

    @property
    def remaining(self):
        """Remaining = Expected - Paid, but never below 0 (per Excel logic)."""
        return max(0.0, float(self.expected) - float(self.paid))

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "company_name": self.company.name,
            "year": self.year,
            "month": self.month,
            "expected": float(self.expected),
            "paid": float(self.paid),
            "bonus": float(self.bonus),
            "remaining": self.remaining,
            "notes": self.notes,
        }

    def __str__(self):
        return f"{self.company.name} - {self.year} {self.month}"


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


def _is_certificate_active(certificate):
    if certificate is None:
        return False

    status = str(getattr(certificate, "status", "") or "").strip().lower()
    return status == "active"


def _date_to_iso(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if value:
        return str(value)
    return ""


class BankCertificate(models.Model):
    bank = models.ForeignKey(
        Bank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="certificates",
    )
    currency = models.ForeignKey(
        "Currency", on_delete=models.CASCADE, null=True, blank=True
    )
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    interest_rate = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    interest_value = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    frequency = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=50, default="Active", blank=True)
    last_interest_posted_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
            # 1. Primary Sort: Convert status to lowercase and sink "closed" to the bottom
            # 2. Secondary Sort: Main timeline sequence by Issue Date (Descending)
            # 3. Tertiary Sub-Sort: Exact day component of the Issue Date (Ascending)
            # 4. Fallback Sort: Alphabetical order by Bank Name
            ordering = [
                Case(
                    When(status__iexact="closed", then=Value(1)),
                    # Or using Lower function explicitly if needed for older versions:
                    # When(status=Lower(Value("closed")), then=Value(1)),
                    default=Value(0),
                    output_field=models.IntegerField(),
                ),
                "issue_date__day",
                "bank__name",
            ]

    def to_dict(self):
        return {
            "id": self.id,
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "currency_id": self.currency_id,
            "currency_code": self.currency.code if self.currency else "",
            "currency_symbol": self.currency.symbol if self.currency else "",
            "currency_flag": self.currency.flag if self.currency else "💱",
            "issue_date": (
                self.issue_date.isoformat()
                if isinstance(self.issue_date, (date, datetime))
                else (self.issue_date or "")
            ),
            "expiry_date": (
                self.expiry_date.isoformat()
                if isinstance(self.expiry_date, (date, datetime))
                else (self.expiry_date or "")
            ),
            "amount": float(self.amount),
            "interest_rate": float(self.interest_rate),
            "interest_value": float(self.interest_value),
            "frequency": self.frequency,
            "status": self.status,
            "last_interest_posted_date": (
                self.last_interest_posted_date.isoformat()
                if isinstance(self.last_interest_posted_date, (date, datetime))
                else (self.last_interest_posted_date or "")
            ),
            "notes": self.notes,
        }

    def __str__(self):
        bank_name = self.bank.name if self.bank else "Unknown Bank"
        return f"{bank_name} Certificate {self.id}"


class BankCertificateInterestHistory(models.Model):
    certificate = models.ForeignKey(
        BankCertificate,
        on_delete=models.CASCADE,
        related_name="interest_history",
    )
    posting_date = models.DateField()
    posting_period = models.CharField(max_length=50)
    interest_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    bank = models.ForeignKey(Bank, on_delete=models.SET_NULL, null=True, blank=True)
    currency = models.ForeignKey("Currency", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["posting_date", "id"]
        unique_together = ["certificate", "posting_date"]

    def to_dict(self):
        return {
            "id": self.id,
            "certificate_id": self.certificate_id,
            "posting_date": self.posting_date.isoformat() if self.posting_date else "",
            "posting_period": self.posting_period,
            "interest_amount": float(self.interest_amount or 0),
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "currency_id": self.currency_id,
            "currency_code": self.currency.code if self.currency else "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }

from django.db.models import Sum
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from datetime import date, datetime

# Assuming BalanceEntry and Bank models are in the same models.py file
@receiver(post_save, sender=BankCertificate)
def handle_certificate_save(sender, instance, **kwargs):
    """
    Fires automatically on insert or update of a BankCertificate.
    Calculates total aggregate sum per bank and currency and updates BalanceEntry.
    """
    _sync_certificate_balance(instance.bank_id, instance.currency_id)


@receiver(post_delete, sender=BankCertificate)
def handle_certificate_delete(sender, instance, **kwargs):
    """
    Fires automatically when a BankCertificate is deleted.
    Recalculates balances to ensure zero values or removed allocations clear out.
    """
    _sync_certificate_balance(instance.bank_id, instance.currency_id)


def sync_certificate_balance_entries():
    for bank_id, currency_id in (
        BankCertificate.objects.exclude(bank_id__isnull=True, currency_id__isnull=True)
        .values_list("bank_id", "currency_id")
        .distinct()
    ):
        _sync_certificate_balance(bank_id, currency_id)

    for entry in BalanceEntry.objects.filter(balance_type="certificate"):
        if not entry.bank_id or not entry.currency_id:
            continue
        active_total = sum(
            float(c.amount or 0)
            for c in BankCertificate.objects.filter(
                bank_id=entry.bank_id,
                currency_id=entry.currency_id,
            )
            if _is_certificate_active(c)
        )
        entry.amount = active_total
        entry.save(update_fields=["amount"])


def _sync_certificate_balance(bank_id, currency_id):
    """
    Internal transactional helper to safely aggregate matching certificate fields
    and pipe them down to the parent Balance sheet.
    """
    if not bank_id or not currency_id:
        return

    certs = BankCertificate.objects.filter(bank_id=bank_id, currency_id=currency_id)
    total_amount = sum(
        float(c.amount or 0)
        for c in certs
        if _is_certificate_active(c)
    )

    if total_amount > 0:
        # Build standard engineering title syntax dynamically safely from foreign object tracking
        try:
            bank_instance = Bank.objects.get(pk=bank_id)
            title_text = f"{bank_instance.name} Certificates Balance"
        except Bank.DoesNotExist:
            title_text = "Certificates Balance"

        # Update matching row or build a clean new asset profile block automatically
        BalanceEntry.objects.update_or_create(
            balance_type="certificate",
            bank_id=bank_id,
            currency_id=currency_id,
            defaults={
                "title": title_text,
                "amount": total_amount,
                "notes": "Automated system synchronization from active bank certificates profile pipeline."
            }
        )
    else:
        # Cascade-delete or remove redundant balance references if aggregate returns empty sets
        BalanceEntry.objects.filter(
            balance_type="certificate",
            bank_id=bank_id,
            currency_id=currency_id
        ).delete()
        
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


class BalanceEntry(models.Model):
    title = models.CharField(max_length=200)
    
    # Clean, scalable choice definition
    class BalanceType(models.TextChoices):
        CASH = "cash", "Cash"
        BANK = "bank", "Bank Account"
        GOLD = "gold", "Gold"  # Matches frontend value="gold"
        CERTIFICATE = "certificate", "Certificate"

    balance_type = models.CharField(
        max_length=20,
        choices=BalanceType.choices,
        default=BalanceType.CASH
    )
    bank = models.ForeignKey(Bank, on_delete=models.SET_NULL, null=True, blank=True)
    currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE, null=True, blank=True
    )
    purity = models.CharField(max_length=20, blank=True, default="")
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    entry_date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["title"]

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "balance_type":self.balance_type,
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "currency_id": self.currency_id,
            "currency_code": self.currency.code if self.currency else "",
            "currency_symbol": self.currency.symbol if self.currency else "",
            "currency_flag": self.currency.flag if self.currency else "💱",
            "currency_name": self.currency.name if self.currency else "",
            "purity": self.purity,
            "amount": float(self.amount),
            "notes": self.notes,
        }

    def __str__(self):
        return f"{self.title} ({self.currency.code if self.currency else 'Unknown'})"


class PagePermission(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="page_permissions",
    )
    page = models.CharField(max_length=50, choices=PAGE_PERMISSION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "page"]
        ordering = ["user__username", "page"]

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username,
            "page": self.page,
        }

    def __str__(self):
        return f"{self.user.username} → {self.get_page_display()}"


class AppSettings(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return self.key

    @classmethod
    def get(cls, key, default=None):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key, value):
        obj, _ = cls.objects.update_or_create(key=key, defaults={"value": value})
        return obj


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


# ── Exchange Rates ────────────────────────────────────────────


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

# --- History of gold price-------------------------------------
class GoldPriceHistory(models.Model):

    timestamp = models.DateTimeField(auto_now_add=True)

    carat_24k = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    carat_21k = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    carat_18k = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    usd_gram_24k = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=0
    )

    usd_per_oz = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0
    )

    usd_to_egp = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0
    )

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M}"

# ── Expenses ──────────────────────────────────────────────────


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


# ── User Profile (avatar + full name) ────────────────────────


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=200, blank=True)
    avatar_b64 = models.TextField(blank=True, default="")
    # avatar_b64 stores: "data:image/jpeg;base64,/9j/4AAQ..." (full data URL)
    bio = models.TextField(blank=True)
    email_verified = models.BooleanField(default=True)
    account_status = models.CharField(max_length=50, default="active")
    status_reason = models.TextField(blank=True, default="")
    preferred_language = models.CharField(max_length=10, blank=True, default="")
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_user_profiles",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rejected_user_profiles",
    )
    disabled_at = models.DateTimeField(null=True, blank=True)
    disabled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disabled_user_profiles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def avatar_url(self):
        """Returns the base64 data URL directly — no file system needed."""
        return self.avatar_b64 if self.avatar_b64 else None

    def display_name(self):
        return self.full_name or self.user.get_full_name() or self.user.username

    def to_dict(self):
        return {
            "full_name": self.full_name,
            "avatar_url": self.avatar_url(),
            "bio": self.bio,
            "email_verified": self.email_verified,
            "account_status": self.account_status,
            "status_reason": self.status_reason,
            "preferred_language": self.preferred_language,
        }

    def __str__(self):
        return f"Profile({self.user.username})"


AUTH_ACCOUNT_STATUS_CHOICES = [
    ("pending_email_verification", "Pending Email Verification"),
    ("pending_admin_approval", "Pending Administrator Approval"),
    ("active", "Active"),
    ("rejected", "Rejected"),
    ("disabled", "Disabled"),
]

AUTH_TOKEN_PURPOSE_CHOICES = [
    ("email_verification", "Email Verification"),
    ("password_reset", "Password Reset"),
    ("admin_approve", "Administrator Approval"),
    ("admin_reject", "Administrator Rejection"),
]

AUTH_AUDIT_EVENT_CHOICES = [
    ("registration", "Registration"),
    ("email_verified", "Email Verified"),
    ("admin_approved", "Administrator Approved"),
    ("admin_rejected", "Administrator Rejected"),
    ("account_disabled", "Account Disabled"),
    ("account_reenabled", "Account Re-enabled"),
    ("password_reset_requested", "Password Reset Requested"),
    ("password_reset_completed", "Password Reset Completed"),
]


class AuthToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="auth_tokens")
    purpose = models.CharField(max_length=50, choices=AUTH_TOKEN_PURPOSE_CHOICES)
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def is_expired(self):
        return bool(self.expires_at and timezone.now() >= self.expires_at)

    def is_usable(self):
        return self.used_at is None and not self.is_expired()

    def __str__(self):
        return f"AuthToken({self.user.username}, {self.purpose})"


class EmailTemplate(models.Model):
    key = models.CharField(max_length=100, unique=True)
    subject_translations = models.JSONField(default=dict, blank=True)
    body_translations = models.JSONField(default=dict, blank=True)
    description_translations = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def get_subject(self, lang="en"):
        return (self.subject_translations or {}).get(lang) or (self.subject_translations or {}).get("en", "")

    def get_body(self, lang="en"):
        return (self.body_translations or {}).get(lang) or (self.body_translations or {}).get("en", "")

    def get_description(self, lang="en"):
        return (self.description_translations or {}).get(lang) or (self.description_translations or {}).get("en", "")

    def to_dict(self, lang="en"):
        return {
            "id": self.id,
            "key": self.key,
            "subject": self.get_subject(lang),
            "body": self.get_body(lang),
            "description": self.get_description(lang),
            "subject_translations": self.subject_translations or {},
            "body_translations": self.body_translations or {},
            "description_translations": self.description_translations or {},
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }

    def __str__(self):
        return self.key


class AuthAuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="auth_audit_logs")
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auth_audit_actions",
    )
    event_type = models.CharField(max_length=50, choices=AUTH_AUDIT_EVENT_CHOICES)
    details = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"AuthAuditLog({self.user.username}, {self.event_type})"


# ════════════════════════════════════════════════════════════
# Feature: Reminder Engine
# ════════════════════════════════════════════════════════════

REMINDER_TYPE_CHOICES = [
    ("cert_maturity", "Certificate Maturity"),
    ("insurance_expiry", "Insurance Expiry"),
    ("vehicle_license_expiry", "Vehicle License Expiry"),
    ("property_tax_reminder", "Property Tax Reminder"),
    ("salary_unpaid", "Salary Unpaid"),
    ("salary_day", "Salary Day"),
    ("custom", "Custom"),
]

SALARY_TRIGGER_CHOICES = [
    ("day_of_month", "Day of Month"),
    ("days_before_eom", "Days Before End of Month"),
    ("days_after_som", "Days After Start of Month"),
]


class ReminderRule(models.Model):
    """Fully configurable reminder rule — no hardcoded values."""

    name = models.CharField(max_length=200)
    rule_type = models.CharField(
        max_length=50, choices=REMINDER_TYPE_CHOICES, default="cert_maturity"
    )
    is_active = models.BooleanField(default=True)

    # Certificate maturity fields
    days_before = models.IntegerField(
        default=30, help_text="Days before expiry (cert_maturity)"
    )

    # Salary fields
    salary_trigger = models.CharField(
        max_length=50,
        choices=SALARY_TRIGGER_CHOICES,
        default="day_of_month",
        blank=True,
    )
    salary_day = models.IntegerField(
        default=25, help_text="Trigger value for salary reminder"
    )
    salary_message = models.CharField(
        max_length=300,
        blank=True,
        default="Salary reminder: check if this month has been paid",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["rule_type", "name"]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "rule_type": self.rule_type,
            "rule_type_label": dict(REMINDER_TYPE_CHOICES).get(
                self.rule_type, self.rule_type
            ),
            "is_active": self.is_active,
            "days_before": self.days_before,
            "salary_trigger": self.salary_trigger,
            "salary_trigger_label": dict(SALARY_TRIGGER_CHOICES).get(
                self.salary_trigger, ""
            ),
            "salary_day": self.salary_day,
            "salary_message": self.salary_message,
            "created_at": self.created_at.strftime("%Y-%m-%d"),
        }

    def __str__(self):
        return f"{self.name} ({self.rule_type})"


# ════════════════════════════════════════════════════════════
# Feature: Certificate Status (configurable)
# ════════════════════════════════════════════════════════════


class CertificateStatus(models.Model):
    """Admin-configurable certificate lifecycle statuses."""

    name = models.CharField(max_length=100, unique=True)
    color_hex = models.CharField(max_length=7, default="#1a6ef5")
    is_default = models.BooleanField(
        default=False, help_text="Used as default status for new certs"
    )
    is_terminal = models.BooleanField(
        default=False, help_text="No further renewals expected"
    )
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "color_hex": self.color_hex,
            "is_default": self.is_default,
            "is_terminal": self.is_terminal,
            "order": self.order,
        }

    def __str__(self):
        return self.name


# ════════════════════════════════════════════════════════════
# Feature: Reminder Log (tracks fired reminders to avoid duplicates)
# ════════════════════════════════════════════════════════════


class ReminderLog(models.Model):
    """Records each time a reminder was shown to avoid daily duplicates."""

    rule = models.ForeignKey(
        ReminderRule, on_delete=models.CASCADE, related_name="logs"
    )
    related_model = models.CharField(max_length=100, blank=True)
    related_id = models.IntegerField(null=True, blank=True)
    fired_on = models.DateField(auto_now_add=True)
    message = models.TextField(blank=True)

    class Meta:
        unique_together = ["rule", "related_model", "related_id", "fired_on"]
        ordering = ["-fired_on"]

    def to_dict(self):
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "rule_name": self.rule.name,
            "related_model": self.related_model,
            "related_id": self.related_id,
            "fired_on": self.fired_on.isoformat(),
            "message": self.message,
        }
    
class FixedAsset(models.Model):
    name = models.CharField(max_length=200)

    asset_type = models.CharField(
        max_length=30,
        choices=ASSET_TYPES,
    )

    status = models.CharField(
        max_length=20,
        choices=ASSET_STATUS,
        default="Owned",
    )

    purchase_date = models.DateField()

    purchase_price = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    purchase_usd_rate = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
    )

    purchase_price_usd = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    current_market_value = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    valuation_source = models.CharField(
        max_length=20,
        choices=VALUATION_SOURCE,
        default="Manual",
    )

    last_valuation_date = models.DateField(
        null=True,
        blank=True,
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
        ordering = ["name"]

    def _safe_related(self, attr_name):
        try:
            return getattr(self, attr_name)
        except ObjectDoesNotExist:
            return None
        except Exception:
            return None

    def _get_related_details(self):
        type_map = {
            "Real Estate": "real_estate",
            "Vehicles": "vehicle_details",
            "Gold": "gold_details",
            "Other Assets": "other_asset_details",
        }
        relation_name = type_map.get(self.asset_type)
        if not relation_name:
            return None
        return self._safe_related(relation_name)

    def to_dict(self):
        related_details = self._get_related_details()
        real_estate = self._safe_related("real_estate")
        vehicle_details = self._safe_related("vehicle_details")
        gold_details = self._safe_related("gold_details")
        other_asset_details = self._safe_related("other_asset_details")
        sale = self._safe_related("sale")
        mortgage = self._safe_related("mortgage")
        rental = self._safe_related("rental")
        return {
            "id": self.id,
            "name": self.name,
            "asset_type": self.asset_type,
            "status": self.status,
            "purchase_date": (
                self.purchase_date.isoformat()
                if hasattr(self.purchase_date, "isoformat")
                else self.purchase_date
            ),
            "purchase_price": float(self.purchase_price),
            "purchase_usd_rate": float(self.purchase_usd_rate),
            "purchase_price_usd": float(self.purchase_price_usd),
            "current_market_value": float(self.current_market_value),
            "valuation_source": self.valuation_source,
            "last_valuation_date": (
                self.last_valuation_date.isoformat()
                if hasattr(self.last_valuation_date, "isoformat")
                else self.last_valuation_date
            ),
            "notes": self.notes,

            "details": related_details.to_dict() if related_details else None,

            # Related Models
            "real_estate": (
                real_estate.to_dict()
                if real_estate
                else None
            ),

            "vehicle_details": (
                vehicle_details.to_dict()
                if vehicle_details
                else None
            ),

            "gold_details": (
                gold_details.to_dict()
                if gold_details
                else None
            ),

            "other_asset_details": (
                other_asset_details.to_dict()
                if other_asset_details
                else None
            ),

            "renovations": [
                item.to_dict()
                for item in self.renovations.all()
            ],

            "maintenance": [
                item.to_dict()
                for item in self.maintenance.all()
            ],

            "insurance": [
                item.to_dict()
                for item in self.insurance.all()
            ],

            "furniture": [
                item.to_dict()
                for item in self.furniture.all()
            ],

            "valuation_history": [
                item.to_dict()
                for item in self.valuation_history.all()
            ],

            "sale": (
                sale.to_dict()
                if sale
                else None
            ),

            "mortgage": (
                mortgage.to_dict()
                if mortgage
                else None
            ),

            "rental": (
                rental.to_dict()
                if rental
                else None
            ),

            "photos": [
                photo.to_dict()
                for photo in self.photos.all()
            ],
        }
    def save(self, *args, **kwargs):
        if self.purchase_usd_rate and self.purchase_usd_rate > 0:
            self.purchase_price_usd = (
                Decimal(self.purchase_price) /
                Decimal(self.purchase_usd_rate)
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
        
class RealEstateDetails(models.Model):
    asset = models.OneToOneField(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="real_estate",
    )

    country = models.CharField(max_length=100, default="Egypt")
    governorate = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    full_address = models.TextField(blank=True)

    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    area_m2 = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    bedrooms = models.PositiveSmallIntegerField(default=0)
    bathrooms = models.PositiveSmallIntegerField(default=0)

    floor_number = models.PositiveSmallIntegerField(default=0)
    building_floors = models.PositiveSmallIntegerField(default=0)

    build_year = models.PositiveSmallIntegerField(null=True, blank=True)

    has_elevator = models.BooleanField(default=False)
    has_garage = models.BooleanField(default=False)
    has_gas = models.BooleanField(default=False)

    electricity_meter_private = models.BooleanField(default=True)
    water_meter_private = models.BooleanField(default=False)

    has_land_share = models.BooleanField(default=False)
    land_share_ratio = models.CharField(max_length=50, blank=True)

    facing = models.CharField(max_length=100, blank=True)

    licensed = models.BooleanField(default=False)
    land_share_sqm = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True)

    finishing_level = models.CharField(max_length=100, blank=True)

    last_estimated_market_price = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
    )

    last_valuation_date = models.DateField(
        null=True,
        blank=True,
    )

    valuation_provider = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    furnished_status = models.CharField(
        max_length=50,
        choices=[
            ("Unfurnished", "Unfurnished"),
            ("Semi Furnished", "Semi Furnished"),
            ("Fully Furnished", "Fully Furnished"),
        ],
        default="Unfurnished",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_dict(self):
        return {
            "country": self.country,
            "governorate": self.governorate,
            "city": self.city,
            "district": self.district,
            "address": self.full_address,
            "rooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "floor": self.floor_number,
            "building_floors": self.building_floors,
            "building_year": self.build_year,
            "facades": self.facing,
            "finishing_level": self.finishing_level,
            "furnished_status": self.furnished_status,
            "electricity": self.electricity_meter_private,
            "water": self.water_meter_private,
            "gas": self.has_gas,
            "elevator": self.has_elevator,
            "garage": self.has_garage,
            "has_land_share":self.has_land_share,
            "land_share": self.land_share_ratio,
            "apartment_area": float(self.area_m2),
            "land_area": float(self.land_share_sqm),
            "latitude": float(self.latitude) if self.latitude else None,
            "longitude": float(self.longitude) if self.longitude else None,
            "licensed": self.licensed,
            "description": self.description,
            "last_estimated_market_price": float(self.last_estimated_market_price) if self.last_estimated_market_price is not None else None,
            "last_valuation_date": self.last_valuation_date.isoformat() if self.last_valuation_date else "",
            "valuation_provider": self.valuation_provider,
        }

    def __str__(self):
        return f"{self.asset.name} Details"


class VehicleDetails(models.Model):
    asset = models.OneToOneField(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="vehicle_details",
    )
    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    vin = models.CharField(max_length=100, blank=True)
    engine = models.CharField(max_length=100, blank=True)
    transmission = models.CharField(max_length=100, blank=True)
    fuel_type = models.CharField(max_length=50, blank=True)
    mileage = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    plate_number = models.CharField(max_length=100, blank=True)
    license_expiry_date = models.DateField(null=True, blank=True)
    color = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            "brand": self.brand,
            "model": self.model,
            "year": self.year,
            "vin": self.vin,
            "engine": self.engine,
            "transmission": self.transmission,
            "fuel_type": self.fuel_type,
            "mileage": float(self.mileage or 0),
            "plate_number": self.plate_number,
            "license_expiry_date": self.license_expiry_date.isoformat() if self.license_expiry_date else "",
            "color": self.color,
        }


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


class OtherAssetDetails(models.Model):
    asset = models.OneToOneField(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="other_asset_details",
    )
    category = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            "category": self.category,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "serial_number": self.serial_number,
            "description": self.description,
            "warranty_expiry": self.warranty_expiry.isoformat() if self.warranty_expiry else "",
            "notes": self.notes,
        }


class AssetMaintenance(models.Model):
    asset = models.ForeignKey(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="maintenance",
    )
    date = models.DateField()
    maintenance_type = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "id"]

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "date": self.date.isoformat() if self.date else "",
            "type": self.maintenance_type,
            "cost": float(self.cost or 0),
            "notes": self.notes,
        }


class AssetInsurance(models.Model):
    asset = models.ForeignKey(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="insurance",
    )
    company = models.CharField(max_length=200)
    policy_number = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    premium = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["expiry_date", "id"]

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "company": self.company,
            "policy_number": self.policy_number,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else "",
            "premium": float(self.premium or 0),
        }

class AssetRenovation(models.Model):
    asset = models.ForeignKey(
        FixedAsset,
        on_delete=models.CASCADE,
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
            "date": self.date.isoformat() if self.date else "",
            "category": self.category,
            "description": self.description,
            "amount_egp": float(self.amount_egp),
            "usd_rate": float(self.usd_rate),
            "amount_usd": float(self.amount_usd),
            "notes": self.notes,
        }
    
    def __str__(self):
        return f"{self.asset.name} - {self.category}"

class AssetFurniture(models.Model):
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
                if self.purchase_date
                else ""
            ),
            "amount_egp": float(self.amount_egp),
            "usd_rate": float(self.usd_rate),
            "amount_usd": float(self.amount_usd),
            "quantity": self.quantity,
            "notes": self.notes,
        }

    def __str__(self):
        return f"{self.asset.name} - {self.name}"

class AssetPhoto(models.Model):
    asset = models.ForeignKey(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="photos",
    )

    image_data = models.BinaryField(
        null=True,
        blank=True
    )
    filename = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
    mime_type = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    title = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["uploaded_at"]

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "filename": self.filename,
            "url": f"/api/fixed-assets/photo/{self.id}/",
        }

    def __str__(self):
        return self.title or f"Photo #{self.id}"
    
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

class AssetSale(models.Model):
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
        "BalanceEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_sales",
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def to_dict(self):
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
            "notes": self.notes,
        }

    def __str__(self):
        return f"{self.asset.name} Sold"


class AssetMortgage(models.Model):
    asset = models.OneToOneField(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="mortgage",
    )

    loan_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    remaining_balance = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    monthly_installment = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    interest_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=0,
    )

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_dict(self):
        current_market_value = float(self.asset.current_market_value or 0)
        remaining_balance = float(self.remaining_balance or 0)
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "loan_amount": float(self.loan_amount or 0),
            "remaining_balance": remaining_balance,
            "monthly_installment": float(self.monthly_installment or 0),
            "interest_rate": float(self.interest_rate or 0),
            "start_date": _date_to_iso(self.start_date),
            "end_date": _date_to_iso(self.end_date),
            "net_equity": current_market_value - remaining_balance,
        }


@receiver(post_save, sender=AssetMortgage)
def handle_asset_mortgage_save(sender, instance, **kwargs):
    from core.services.financial_sync_service import FinancialSyncService

    FinancialSyncService().sync_mortgage_balance(instance)


@receiver(post_delete, sender=AssetMortgage)
def handle_asset_mortgage_delete(sender, instance, **kwargs):
    from core.services.financial_sync_service import FinancialSyncService

    FinancialSyncService().sync_deleted_mortgage_balance(instance)


class AssetRental(models.Model):
    asset = models.OneToOneField(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name="rental",
    )

    monthly_rent = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    occupancy_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    tenant_name = models.CharField(max_length=200, blank=True)
    contract_start = models.DateField(null=True, blank=True)
    contract_end = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_dict(self):
        monthly_rent = float(self.monthly_rent or 0)
        annual_rent = monthly_rent * 12
        current_market_value = float(self.asset.current_market_value or 0)
        rental_yield = (annual_rent / current_market_value * 100) if current_market_value > 0 else 0
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "monthly_rent": monthly_rent,
            "annual_rent": annual_rent,
            "occupancy_rate": float(self.occupancy_rate or 0),
            "rental_yield": rental_yield,
            "tenant_name": self.tenant_name,
            "contract_start": _date_to_iso(self.contract_start),
            "contract_end": _date_to_iso(self.contract_end),
            "notes": self.notes,
        }


class Document(models.Model):
    parent_object_type = models.CharField(max_length=100, db_index=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(db_index=True)
    parent_object = GenericForeignKey("content_type", "object_id")

    document_category = models.CharField(max_length=100)
    original_file_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField()
    file_content = models.BinaryField()
    file_hash = models.CharField(max_length=64, blank=True, db_index=True)

    upload_date = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-upload_date", "-id"]
        indexes = [
            models.Index(fields=["parent_object_type", "content_type", "object_id"]),
        ]

    def to_dict(self):
        return {
            "id": self.id,
            "parent_object_type": self.parent_object_type,
            "parent_object_id": self.object_id,
            "document_category": self.document_category,
            "original_file_name": self.original_file_name,
            "mime_type": self.mime_type,
            "file_size": int(self.file_size or 0),
            "upload_date": self.upload_date.isoformat() if self.upload_date else "",
            "uploaded_by": getattr(self.uploaded_by, "username", ""),
            "notes": self.notes,
        }


@receiver(post_save, sender=AssetRental)
def handle_asset_rental_save(sender, instance, **kwargs):
    from core.services.financial_sync_service import FinancialSyncService

    FinancialSyncService().sync_rental_balance(instance)


@receiver(post_delete, sender=AssetRental)
def handle_asset_rental_delete(sender, instance, **kwargs):
    from core.services.financial_sync_service import FinancialSyncService

    FinancialSyncService().sync_deleted_rental_balance(instance)


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
    from core.services.financial_sync_service import FinancialSyncService

    FinancialSyncService().sync_asset_sale_balance(instance)


@receiver(post_delete, sender=AssetSale)
def handle_asset_sale_delete(sender, instance, **kwargs):
    from core.services.financial_sync_service import FinancialSyncService

    FinancialSyncService().sync_deleted_asset_sale_balance(instance)