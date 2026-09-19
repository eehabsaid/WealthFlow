"""
Module-name -> test-function dispatch table for the human QA E2E suite
entrypoint.

Split out of the former monolithic scripts/test_ui_human_full_e2e.py
(200-line rule). Kept as a flat sibling file, imported with a bare
`import` (no `scripts.` prefix) since test_ui_human_full_e2e.py is
invoked directly (`python scripts/test_ui_human_full_e2e.py`), which
puts the scripts/ directory itself on sys.path rather than the repo
root.
"""

from tests.modules.authentication import test_authentication_module
from tests.modules.dashboard import test_dashboard_module
from tests.modules.balance import test_balance_module
from tests.modules.salary import test_salary_module
from tests.modules.expenses import test_expenses_module
from tests.modules.certificates import test_certificates_module
from tests.modules.fixed_assets import test_fixed_assets_module
from tests.modules.reports import test_reports_module
from tests.modules.reminders import test_reminders_module
from tests.modules.financial_advisor import test_financial_advisor_module
from tests.modules.ai import test_ai_module
from tests.modules.settings import test_settings_module
from tests.modules.translations import test_translations_module
from tests.modules.billing import test_billing_module

MODULE_DISPATCH = {
    "auth": test_authentication_module,
    "dashboard": test_dashboard_module,
    "ai": test_ai_module,
    "balance": test_balance_module,
    "salary": test_salary_module,
    "certificates": test_certificates_module,
    "fixed_assets": test_fixed_assets_module,
    "expenses": test_expenses_module,
    "reports": test_reports_module,
    "reminders": test_reminders_module,
    "financial_advisor": test_financial_advisor_module,
    "settings": test_settings_module,
    "translations": test_translations_module,
    "billing": test_billing_module,
}


def run_module(mod, ctx, reporter, screenshot_logger):
    MODULE_DISPATCH[mod](ctx, reporter, screenshot_logger)
