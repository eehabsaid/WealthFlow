# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false
"""Market data, gold and AI settings tabs.

Part of the umbrella in core/views/settings/__init__.py (split so no file passes ~200 lines)."""

from core.views.settings.gold.gold_settings_helpers import _seed_gold_settings_defaults
from core.views.settings.gold.gold_type_settings_views import (
    GoldTypeSettingsListView,
    GoldTypeSettingsDetailView,
)
from core.views.settings.gold.gold_purity_settings_views import (
    GoldPuritySettingsListView,
    GoldPuritySettingsDetailView,
)
from core.views.settings.market.exchange_rate_views import (
    ExchangeRateListView,
    ExchangeRateRefreshView,
)
from core.views.settings.market.gold_price_views import (
    GoldPriceListView,
    GoldPriceRefreshView,
)
from ai.views.settings.ai_settings_views import AISettingsView
from ai.views.settings.ai_user_limits_views import AIUserLimitsView
from ai.views.settings.ai_user_settings_views import AIUserSettingsView
from ai.views.settings.ai_connection_test_views import AIConnectionTestView
from ai.views.settings.ai_provider_views import AIProviderListView
from ai.views.settings.ai_runtime_capabilities_views import AIRuntimeCapabilitiesView

__all__ = [
    "_seed_gold_settings_defaults",
    "GoldTypeSettingsListView",
    "GoldTypeSettingsDetailView",
    "GoldPuritySettingsListView",
    "GoldPuritySettingsDetailView",
    "ExchangeRateListView",
    "ExchangeRateRefreshView",
    "GoldPriceListView",
    "GoldPriceRefreshView",
    "AISettingsView",
    "AIUserLimitsView",
    "AIUserSettingsView",
    "AIConnectionTestView",
    "AIProviderListView",
    "AIRuntimeCapabilitiesView",
]
