"""
risk_analysis_service package
==============================
NOTE: Split from the former flat core/services/financial_advisor/risk_analysis_service.py
(542 lines) per the project's 200-line file-split rule. Also absorbs the former
stray core/services/financial_advisor/risk_analysis_calculations.py (income
stability calc), folded into risk_analysis_calc_mixin.py since it's the same
"score a risk category" domain as the other five calculators.

Mixin composition pattern (see scenario_planner_service and net_worth_service
packages for the same approach): RiskAnalysisService in risk_analysis_core.py
inherits from four domain mixins, each owning one phase of the payload:

- metrics.py                      -- RiskMetric dataclass, _to_float helper (shared)
- risk_analysis_calc_mixin.py     -- RiskCalcMixin: six per-category risk score calculators
- risk_analysis_findings_mixin.py -- RiskFindingsMixin: findings list, stress tests
- risk_analysis_whatif_mixin.py   -- RiskWhatIfMixin: what-if sensitivity projections
- risk_analysis_actions_mixin.py  -- RiskActionsMixin: priority actions, overall recommendation
- risk_analysis_core.py           -- RiskAnalysisService: constructor, _determine_level,
                                      _gather_income_sources, payload() orchestration

Import from this package exactly as before the split:
    from core.services.financial_advisor.risk_analysis_service import RiskAnalysisService
"""
from core.services.financial_advisor.risk_analysis_service.risk_analysis_core import RiskAnalysisService
from core.services.financial_advisor.risk_analysis_service.metrics import RiskMetric

__all__ = ["RiskAnalysisService", "RiskMetric"]
