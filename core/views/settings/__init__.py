# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false
"""Umbrella re-export for every settings view, so core/views/__init__.py
can do `from .settings import X` without needing to know whether X lives
in a flat file here or in a per-domain subfolder (ai/, gold/, market/,
user/, documentation/).

ORGANIZING PRINCIPLE: by UI page, not by domain/resource. Every backend
view that only exists to back a tab on the Settings page lives somewhere
under core/views/settings/ — including views for models (Bank, Company,
User, CertificateStatus, ReminderRule) that are also used elsewhere in
the app. The one exception is a view that ISN'T tab-specific even though
it lives in a file that also has tab-specific views (e.g.
FixedAssetValuationRefreshView was split out to
core/views/asset_valuation_views.py because it's a Fixed Assets action,
not a Settings tab, even though it used to sit in the same file as the
Reminders tab views).

STRUCTURE / CONVENTION — read this before adding or splitting a file:
  - A single-resource view file (one Settings tab, e.g. currency_views.py)
    stays flat, directly in this settings/ folder.
  - The moment a domain needs MORE THAN ONE file (because a single file
    would exceed ~200 lines, or because it has natural sub-parts like
    views + helpers), give it its own subfolder here: settings/<domain>/,
    with an empty __init__.py inside it and its files split by concern
    (see settings/ai/, settings/gold/, settings/user/, or
    settings/documentation/ for the pattern).
  - Whenever ANY file in this package — flat or inside a subfolder —
    grows past ~200 lines, split it and, if that produces more than one
    file for that concern, move the results into (or create) a
    settings/<domain>/ subfolder following the same pattern.
  - This package re-exports three umbrella modules (they exist only to keep every file under ~200 lines):
      exports_general.py             currencies, app settings, e-mail, backup, banks, reminders, translations, legal ...
      exports_market_gold_ai.py      gold settings, market data, AI settings
      exports_access_billing_docs.py users/roles, billing (plans, customers ...), documentation
    Add new exports to the matching umbrella module's imports and __all__.
  - Keep this __init__.py's re-exports in sync — this file
    is the single place core/views/__init__.py and core/urls.py depend
    on (both do `from . import views` / `from .settings import X`), so no
    other file needs to change when you reorganize inside settings/.
"""

from core.views.settings import exports_access_billing_docs, exports_general, exports_market_gold_ai

_UMBRELLAS = (exports_general, exports_market_gold_ai, exports_access_billing_docs)

# Bind every re-exported name here so `from core.views.settings import X` keeps working exactly as before
# (no star imports: pyflakes-clean). The names themselves are listed in each umbrella module's __all__.
globals().update({name: getattr(module, name) for module in _UMBRELLAS for name in module.__all__})

__all__ = [name for module in _UMBRELLAS for name in module.__all__]
