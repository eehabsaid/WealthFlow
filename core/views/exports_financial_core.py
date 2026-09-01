"""Umbrella re-export for the Financial Core domain: Salary, Bank
Certificates, Goals, and the Dashboard summary, plus the Company & Bank
setup views (settings/) they depend on. Grouped together because these
are the everyday income/institution/goal-tracking screens, distinct
from Balance/Forecasting (see exports_balance.py).

Whenever salary_views.py, certificate_views.py, goal_views.py,
dashboard_views.py, or the Company/Bank views in settings/ grow and
add/remove a public name, update the imports/__all__ below to match —
this file is what core/views/__init__.py depends on, so no other file
needs to change when those are reorganized internally.
"""

from .settings import CompanyListView, CompanyDetailView, BankListView, BankDetailView, BankWithBalanceListView
from .salary_views import (
    SalaryListView,
    SalaryDetailView,
    GenerateCurrentSalaryView,
    MarkSalaryPaidView,
    SalarySummaryView,
    PerDiemListView,
    PerDiemDetailView,
    PerDiemCurrencyListView,
)
from .certificate_views import (
    BankCertificateListView,
    BankCertificateDetailView,
    BankCertificateInterestHistoryView,
    _run_certificate_interest_sync,
)
from .goal_views import GoalPlanningView, GoalListView, GoalDetailView
from .dashboard_views import DashboardSummaryView, index, _api_auth_required, _parse_iso_date

__all__ = [
    "CompanyListView",
    "CompanyDetailView",
    "BankListView",
    "BankDetailView",
    "BankWithBalanceListView",
    "SalaryListView",
    "SalaryDetailView",
    "GenerateCurrentSalaryView",
    "MarkSalaryPaidView",
    "SalarySummaryView",
    "PerDiemListView",
    "PerDiemDetailView",
    "PerDiemCurrencyListView",
    "BankCertificateListView",
    "BankCertificateDetailView",
    "BankCertificateInterestHistoryView",
    "_run_certificate_interest_sync",
    "GoalPlanningView",
    "GoalListView",
    "GoalDetailView",
    "DashboardSummaryView",
    "index",
    "_api_auth_required",
    "_parse_iso_date",
]
