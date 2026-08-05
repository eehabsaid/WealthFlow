from django.contrib import admin
from .models import Company, SalaryEntry, Bank, BalanceEntry, AppSettings, BankCertificate, Currency, ExchangeRate, GoldPrice, PagePermission, CurrencyExchange

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
