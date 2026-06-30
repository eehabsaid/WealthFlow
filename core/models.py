from datetime import date, datetime

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

ASSET_TYPES = [
    ("Apartment", "Apartment"),
    ("Villa", "Villa"),
    ("Land", "Land"),
    ("Shop", "Shop"),
    ("Office", "Office"),
    ("Car", "Car"),
    ("Other", "Other"),
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
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issue_date", "bank__name"]

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
            "notes": self.notes,
        }

    def __str__(self):
        bank_name = self.bank.name if self.bank else "Unknown Bank"
        return f"{bank_name} Certificate {self.id}"

from django.db.models import Sum
from django.db.models.signals import post_save, post_delete
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


def _sync_certificate_balance(bank_id, currency_id):
    """
    Internal transactional helper to safely aggregate matching certificate fields
    and pipe them down to the parent Balance sheet.
    """
    if not bank_id or not currency_id:
        return

    # Aggregate total sum of active/available certificates for this bank & currency combo
    total_amount = BankCertificate.objects.filter(
        bank_id=bank_id, 
        currency_id=currency_id
    ).aggregate(total=Sum('amount'))['total'] or 0

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
        }

    def __str__(self):
        return f"Profile({self.user.username})"


# ════════════════════════════════════════════════════════════
# Feature: Reminder Engine
# ════════════════════════════════════════════════════════════

REMINDER_TYPE_CHOICES = [
    ("cert_maturity", "Certificate Maturity"),
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

    def to_dict(self):
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

            # Related Models
            "real_estate": (
                self.real_estate.to_dict()
                if hasattr(self, "real_estate")
                else None
            ),

            "renovations": [
                item.to_dict()
                for item in self.renovations.all()
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
                self.sale.to_dict()
                if hasattr(self, "sale")
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
        }

    def __str__(self):
        return f"{self.asset.name} Details"

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