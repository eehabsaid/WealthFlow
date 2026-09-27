"""Re-exports preserving the pre-split import path
`core.services.ai.providers.expenses_provider` (now a package, was a single
module) — see decisions-and-conventions: split oversized modules into
packages with __init__.py re-exports preserving import paths.
"""

from core.services.ai.providers.expenses_provider.provider import (
    MAX_MONTHLY_CATEGORY_BREAKDOWN_MONTHS_FOR_AI,
    MAX_MONTHLY_SUMMARY_MONTHS_FOR_AI,
    MAX_RECENT_EXPENSES_FOR_AI,
    ExpensesDataProvider,
)

__all__ = [
    "ExpensesDataProvider",
    "MAX_RECENT_EXPENSES_FOR_AI",
    "MAX_MONTHLY_SUMMARY_MONTHS_FOR_AI",
    "MAX_MONTHLY_CATEGORY_BREAKDOWN_MONTHS_FOR_AI",
]
