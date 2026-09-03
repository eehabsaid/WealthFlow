"""URL configuration package, split by domain for maintainability.

Sibling modules:
- auth_urls.py: accounts, api/auth, users, user-management
- financial_core_urls.py: rates, gold, salary, per-diems, banks, balance, expenses
- settings_urls.py: reports/generate, settings, ai settings, backup, documentation engine, excel export
- misc_urls.py: reminders, cert-statuses, translations, advanced reports, dashboard, goals, documents
- fixed_assets_urls.py: fixed assets, renovations, acquisition costs, furniture, valuations, maintenance, insurance
- financial_advisor_urls.py: forecasts, overview, optimizer, risk analysis, scenarios, goal planning, ai chat
- ai_platform_urls.py: knowledge base, datasets, models, benchmarks, prompt library

All lists are concatenated below to form the single `urlpatterns` Django expects.
"""

from .auth_urls import urlpatterns as auth_urlpatterns
from .financial_core_urls import urlpatterns as financial_core_urlpatterns
from .settings_urls import urlpatterns as settings_urlpatterns
from .misc_urls import urlpatterns as misc_urlpatterns
from .fixed_assets_urls import urlpatterns as fixed_assets_urlpatterns
from .financial_advisor_urls import urlpatterns as financial_advisor_urlpatterns
from .ai_platform_urls import urlpatterns as ai_platform_urlpatterns

urlpatterns = (
    auth_urlpatterns
    + financial_core_urlpatterns
    + settings_urlpatterns
    + misc_urlpatterns
    + fixed_assets_urlpatterns
    + financial_advisor_urlpatterns
    + ai_platform_urlpatterns
)
