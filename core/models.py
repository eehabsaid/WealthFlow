from datetime import date,datetime

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
PAGE_PERMISSION_CHOICES = [
    ('dashboard', 'Dashboard'),
    ('companies', 'Companies'),
    ('salary', 'Salary'),
    ('banks', 'Banks'),
    ('bank_certificates', 'Bank Certificates'),
    ('currencies', 'Currencies'),
    ('balance', 'Balance'),
    ('settings', 'Settings'),
    ('expense-categories', 'Expense Categories'),
    ('exchange_rates', 'Exchange Rates'),
    ('gold_price', 'Gold Price'),
    ('user_management', 'User Management'),
    ('expenses', 'Expenses'),
    ('reports', 'Reports'),
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
    bank = models.ForeignKey(Bank, on_delete=models.SET_NULL, null=True, blank=True, related_name="certificates")
    currency = models.ForeignKey("Currency", on_delete=models.CASCADE, null=True, blank=True)
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
            "issue_date": self.issue_date.isoformat() if isinstance(self.issue_date, (date, datetime)) else (self.issue_date or ""),
            "expiry_date": self.expiry_date.isoformat() if isinstance(self.expiry_date, (date, datetime)) else (self.expiry_date or ""),
            "amount": float(self.amount),
            "interest_rate": float(self.interest_rate),
            "interest_value": float(self.interest_value),
            "frequency": self.frequency,
            "status": self.status,
            "notes": self.notes,
        }

    def __str__(self):
        bank_name = self.bank.name if self.bank else 'Unknown Bank'
        return f"{bank_name} Certificate {self.id}"


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
    bank = models.ForeignKey(Bank, on_delete=models.SET_NULL, null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    entry_date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["title"]

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='page_permissions')
    page = models.CharField(max_length=50, choices=PAGE_PERMISSION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'page']
        ordering = ['user__username', 'page']

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username,
            'page': self.page,
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
    currency_code   = models.CharField(max_length=10)   # USD, EUR, SAR …
    currency_name   = models.CharField(max_length=100, blank=True)
    buy_rate        = models.DecimalField(max_digits=14, decimal_places=6, default=0)
    sell_rate       = models.DecimalField(max_digits=14, decimal_places=6, default=0)
    mid_rate        = models.DecimalField(max_digits=14, decimal_places=6, default=0)
    source          = models.CharField(max_length=50, default="open.er-api.com")
    fetched_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fetched_at", "currency_code"]

    def to_dict(self):
        return {
            "id":            self.id,
            "currency_code": self.currency_code,
            "currency_name": self.currency_name,
            "buy_rate":      float(self.buy_rate),
            "sell_rate":     float(self.sell_rate),
            "mid_rate":      float(self.mid_rate),
            "source":        self.source,
            "fetched_at":    self.fetched_at.strftime("%Y-%m-%d %H:%M") if self.fetched_at else "",
        }

    def __str__(self):
        return f"{self.currency_code} → EGP  mid={self.mid_rate}"


class GoldPrice(models.Model):
    """One row per fetch. Stores EGP price per gram for common carats."""
    # Sell prices (EGP per gram)
    carat_24k   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    carat_22k   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    carat_21k   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    carat_18k   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Buy prices (EGP per gram)
    carat_24k_buy = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    carat_22k_buy = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    carat_21k_buy = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    carat_18k_buy = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Raw USD per gram values stored so user can see them too
    usd_gram_24k = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    usd_per_oz   = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    usd_to_egp   = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    source_gold  = models.CharField(max_length=100, default="api.gold-api.com")
    source_fx    = models.CharField(max_length=100, default="open.er-api.com")
    fetched_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fetched_at"]

    def to_dict(self):
        return {
            "id":          self.id,
            "carat_24k":   float(self.carat_24k),
            "carat_22k":   float(self.carat_22k),
            "carat_21k":   float(self.carat_21k),
            "carat_18k":   float(self.carat_18k),
            "carat_24k_buy": float(self.carat_24k_buy),
            "carat_22k_buy": float(self.carat_22k_buy),
            "carat_21k_buy": float(self.carat_21k_buy),
            "carat_18k_buy": float(self.carat_18k_buy),
            "usd_gram_24k":float(self.usd_gram_24k),
            "usd_per_oz":  float(self.usd_per_oz),
            "usd_to_egp":  float(self.usd_to_egp),
            "source_gold": self.source_gold,
            "source_fx":   self.source_fx,
            "fetched_at":  self.fetched_at.strftime("%Y-%m-%d %H:%M") if self.fetched_at else "",
        }

    def __str__(self):
        return f"Gold {self.fetched_at}  21K={self.carat_21k} EGP/g"


# ── Expenses ──────────────────────────────────────────────────

class ExpenseCategory(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    icon        = models.CharField(max_length=10, default="💰")
    color_hex   = models.CharField(max_length=7, default="#0d6efd")
    order       = models.IntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "name"]

    def to_dict(self):
        return {
            "id": self.id, "name": self.name,
            "icon": self.icon, "color_hex": self.color_hex, "order": self.order,
        }

    def __str__(self):
        return self.name


class ExpenseSubcategory(models.Model):
    category   = models.ForeignKey(
        ExpenseCategory, on_delete=models.CASCADE, related_name="subcategories")
    name       = models.CharField(max_length=100)
    order      = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "name"]
        unique_together = ["category", "name"]

    def to_dict(self):
        return {
            "id": self.id, "name": self.name,
            "category_id": self.category_id,
            "category_name": self.category.name,
            "category_icon": self.category.icon,
            "category_color": self.category.color_hex,
            "order": self.order,
        }

    def __str__(self):
        return f"{self.category.name} / {self.name}"


class Expense(models.Model):
    date           = models.DateField()
    year           = models.IntegerField()
    month          = models.IntegerField()   # 1-12
    category       = models.ForeignKey(
        ExpenseCategory, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="expenses")
    subcategory    = models.ForeignKey(
        ExpenseSubcategory, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="expenses")
    description    = models.CharField(max_length=300, blank=True)
    amount         = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency       = models.ForeignKey(
        Currency, on_delete=models.SET_NULL, null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True,
        choices=[("Cash","Cash"),("Card","Card"),("Bank Transfer","Bank Transfer"),("Other","Other")])
    notes          = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]

    def to_dict(self):
        return {
            "id":             self.id,
            "date":           self.date.isoformat() if self.date else "",
            "year":           self.year,
            "month":          self.month,
            "category_id":    self.category_id,
            "category_name":  self.category.name  if self.category  else "",
            "category_icon":  self.category.icon  if self.category  else "💰",
            "category_color": self.category.color_hex if self.category else "#0d6efd",
            "subcategory_id":   self.subcategory_id,
            "subcategory_name": self.subcategory.name if self.subcategory else "",
            "description":    self.description,
            "amount":         float(self.amount),
            "currency_code":  self.currency.code   if self.currency  else "EGP",
            "currency_symbol":self.currency.symbol if self.currency  else "ج.م",
            "payment_method": self.payment_method,
            "notes":          self.notes,
        }

    def __str__(self):
        return f"{self.date} {self.category} {self.amount}"


# ── User Profile (avatar + full name) ────────────────────────

class UserProfile(models.Model):
    user       = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile")
    full_name  = models.CharField(max_length=200, blank=True)
    avatar_b64 = models.TextField(blank=True, default="")
    # avatar_b64 stores: "data:image/jpeg;base64,/9j/4AAQ..." (full data URL)
    bio        = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def avatar_url(self):
        """Returns the base64 data URL directly — no file system needed."""
        return self.avatar_b64 if self.avatar_b64 else None

    def display_name(self):
        return self.full_name or self.user.get_full_name() or self.user.username

    def to_dict(self):
        return {
            "full_name":  self.full_name,
            "avatar_url": self.avatar_url(),
            "bio":        self.bio,
        }

    def __str__(self):
        return f"Profile({self.user.username})"


# ════════════════════════════════════════════════════════════
# Feature: Reminder Engine
# ════════════════════════════════════════════════════════════

REMINDER_TYPE_CHOICES = [
    ('cert_maturity',    'Certificate Maturity'),
    ('salary_unpaid',    'Salary Unpaid'),
    ('salary_day',       'Salary Day'),
    ('custom',           'Custom'),
]

SALARY_TRIGGER_CHOICES = [
    ('day_of_month',  'Day of Month'),
    ('days_before_eom', 'Days Before End of Month'),
    ('days_after_som', 'Days After Start of Month'),
]


class ReminderRule(models.Model):
    """Fully configurable reminder rule — no hardcoded values."""
    name            = models.CharField(max_length=200)
    rule_type       = models.CharField(max_length=50, choices=REMINDER_TYPE_CHOICES, default='cert_maturity')
    is_active       = models.BooleanField(default=True)

    # Certificate maturity fields
    days_before     = models.IntegerField(default=30, help_text='Days before expiry (cert_maturity)')

    # Salary fields
    salary_trigger  = models.CharField(max_length=50, choices=SALARY_TRIGGER_CHOICES,
                                       default='day_of_month', blank=True)
    salary_day      = models.IntegerField(default=25, help_text='Trigger value for salary reminder')
    salary_message  = models.CharField(max_length=300, blank=True,
                                       default='Salary reminder: check if this month has been paid')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['rule_type', 'name']

    def to_dict(self):
        return {
            'id':             self.id,
            'name':           self.name,
            'rule_type':      self.rule_type,
            'rule_type_label': dict(REMINDER_TYPE_CHOICES).get(self.rule_type, self.rule_type),
            'is_active':      self.is_active,
            'days_before':    self.days_before,
            'salary_trigger': self.salary_trigger,
            'salary_trigger_label': dict(SALARY_TRIGGER_CHOICES).get(self.salary_trigger, ''),
            'salary_day':     self.salary_day,
            'salary_message': self.salary_message,
            'created_at':     self.created_at.strftime('%Y-%m-%d'),
        }

    def __str__(self):
        return f'{self.name} ({self.rule_type})'


# ════════════════════════════════════════════════════════════
# Feature: Certificate Status (configurable)
# ════════════════════════════════════════════════════════════

class CertificateStatus(models.Model):
    """Admin-configurable certificate lifecycle statuses."""
    name        = models.CharField(max_length=100, unique=True)
    color_hex   = models.CharField(max_length=7, default='#1a6ef5')
    is_default  = models.BooleanField(default=False, help_text='Used as default status for new certs')
    is_terminal = models.BooleanField(default=False, help_text='No further renewals expected')
    order       = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def to_dict(self):
        return {
            'id':          self.id,
            'name':        self.name,
            'color_hex':   self.color_hex,
            'is_default':  self.is_default,
            'is_terminal': self.is_terminal,
            'order':       self.order,
        }

    def __str__(self):
        return self.name


# ════════════════════════════════════════════════════════════
# Feature: Reminder Log (tracks fired reminders to avoid duplicates)
# ════════════════════════════════════════════════════════════

class ReminderLog(models.Model):
    """Records each time a reminder was shown to avoid daily duplicates."""
    rule            = models.ForeignKey(ReminderRule, on_delete=models.CASCADE, related_name='logs')
    related_model   = models.CharField(max_length=100, blank=True)
    related_id      = models.IntegerField(null=True, blank=True)
    fired_on        = models.DateField(auto_now_add=True)
    message         = models.TextField(blank=True)

    class Meta:
        unique_together = ['rule', 'related_model', 'related_id', 'fired_on']
        ordering = ['-fired_on']

    def to_dict(self):
        return {
            'id':            self.id,
            'rule_id':       self.rule_id,
            'rule_name':     self.rule.name,
            'related_model': self.related_model,
            'related_id':    self.related_id,
            'fired_on':      self.fired_on.isoformat(),
            'message':       self.message,
        }
