"""
spending_intelligence_service package
======================================

Structural split of the original flat ``spending_intelligence_service.py``
(204 lines) into mixin modules under 200 lines each, following the
mixin-composition convention used elsewhere in
``core/services/financial_advisor/``.

Modules:
    service.py    - SpendingIntelligenceService orchestrator
                     (__init__, _to_float, payload)
    categories.py - CategoriesMixin: per-category aggregation, most-frequent
                     category, largest expense, registered categories list
    monthly.py    - MonthlyComparisonMixin: overall + per-category monthly
                     totals
    insights.py   - InsightsMixin: AI insight and recommendation generation

External callers continue to import:
    from core.services.financial_advisor.spending_intelligence_service import (
        SpendingIntelligenceService,
    )

No logic changes were made during this split.
"""

from core.services.financial_advisor.spending_intelligence_service.service import (
    SpendingIntelligenceService,
)

__all__ = ["SpendingIntelligenceService"]
