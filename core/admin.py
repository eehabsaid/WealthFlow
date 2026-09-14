from django.contrib import admin
from .models import Company, SalaryEntry, Bank, BalanceEntry, AppSettings, BankCertificate, Currency, ExchangeRate, GoldPrice, PagePermission, CurrencyExchange, Plan, Subscription, Invoice


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "price_egp", "price_usd", "is_active", "sort_order")
    list_editable = ("price_egp", "price_usd", "is_active", "sort_order")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("owner", "plan", "status", "trial_end", "current_period_end", "gateway")
    list_filter = ("status", "plan", "gateway")
    search_fields = ("owner__username", "owner__email")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("owner", "amount", "currency", "status", "issued_at", "paid_at")
    list_filter = ("status", "currency")
    search_fields = ("owner__username", "owner__email")


admin.site.register(Company)
admin.site.register(SalaryEntry)
admin.site.register(Bank)
admin.site.register(BalanceEntry)
admin.site.register(BankCertificate)
admin.site.register(AppSettings)
admin.site.register(Currency)
admin.site.register(ExchangeRate)
admin.site.register(GoldPrice)
admin.site.register(PagePermission)
admin.site.register(CurrencyExchange)
