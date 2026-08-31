# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false
"""Umbrella re-export for every view that backs the Balance page, so
core/views/__init__.py can do `from .balance import X` without needing
to know which file (or subfolder) under core/views/balance/ a given
view lives in.

ORGANIZING PRINCIPLE: by UI page, matching core/views/settings/. Every
backend view that only exists to back a tab on the Balance page lives
here: Accounts, Transfers, Currency Exchange, Bank Interest, and the
Forecasts/Scenario-planning tabs.

STRUCTURE / CONVENTION — read this before adding or splitting a file:
  - A single-resource view file (one Balance tab, e.g.
    balance_transfer_views.py, bank_interest_views.py) stays flat,
    directly in this balance/ folder.
  - The moment a domain needs MORE THAN ONE file (because a single file
    would exceed ~200 lines, or because it has natural sub-parts like
    CRUD + calculations + analysis), give it its own subfolder here:
    balance/<domain>/, with an empty __init__.py inside it and its files
    split by concern (see balance/forecasts/ or settings/ai/ for the
    pattern).
  - Currency Exchange stayed flat (2 files, form-support vs CRUD) since
    that's the whole domain and both files fit comfortably under 200
    lines. Forecasts needed a subfolder because it has 17 view classes
    across genuinely different concerns (forecast payloads, risk/
    performance analysis, scenario CRUD, scenario events, scenario
    comparison).
  - Whenever ANY file in this package grows past ~200 lines, split it
    by concern and, if that produces more than one file, give it its
    own balance/<domain>/ subfolder.
  - Always update this __init__.py's imports/__all__ to match — this
    file is the single place core/views/__init__.py depends on, so no
    other file needs to change when you reorganize inside balance/.
"""

from core.views.balance.balance_account_views import (
    BalanceListView,
    BalanceDetailView,
)
from core.views.balance.balance_transfer_views import (
    BalanceTransferListView,
    BalanceTransferDetailView,
)
from core.views.balance.bank_interest_views import (
    BankInterestListView,
    BankInterestDetailView,
)
from core.views.balance.currency_exchange_form_views import (
    CurrencyExchangeFormOptionsView,
    CurrencyExchangeCalculateView,
)
from core.views.balance.currency_exchange_crud_views import (
    CurrencyExchangeListView,
    CurrencyExchangeDetailView,
)
from core.views.balance.forecasts.forecast_core_views import (
    CertificateForecastView,
    CashFlowForecastView,
    WealthGrowthForecastView,
    PortfolioOptimizerView,
    OverviewView,
)
from core.views.balance.forecasts.forecast_analysis_views import (
    RiskAnalysisView,
    SpendingIntelligenceView,
    OpportunityDetectionView,
    PerformanceView,
    WhatIfSimulatorView,
)
from core.views.balance.forecasts.scenario_crud_views import (
    ScenarioListCreateView,
    ScenarioDetailView,
    ScenarioDuplicateView,
)
from core.views.balance.forecasts.scenario_event_views import (
    ScenarioEventDefinitionsView,
    ScenarioEventListCreateView,
    ScenarioEventDetailView,
)
from core.views.balance.forecasts.scenario_comparison_views import (
    ScenarioComparisonView,
)

__all__ = [
    "BalanceListView",
    "BalanceDetailView",
    "BalanceTransferListView",
    "BalanceTransferDetailView",
    "BankInterestListView",
    "BankInterestDetailView",
    "CurrencyExchangeListView",
    "CurrencyExchangeDetailView",
    "CurrencyExchangeCalculateView",
    "CurrencyExchangeFormOptionsView",
    "CertificateForecastView",
    "CashFlowForecastView",
    "WealthGrowthForecastView",
    "PortfolioOptimizerView",
    "RiskAnalysisView",
    "SpendingIntelligenceView",
    "OpportunityDetectionView",
    "PerformanceView",
    "WhatIfSimulatorView",
    "OverviewView",
    "ScenarioEventDefinitionsView",
    "ScenarioListCreateView",
    "ScenarioDetailView",
    "ScenarioEventListCreateView",
    "ScenarioEventDetailView",
    "ScenarioComparisonView",
    "ScenarioDuplicateView",
]
