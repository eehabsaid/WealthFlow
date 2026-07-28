# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
from typing import Tuple, List, Dict

def determine_level(score: float) -> Tuple[str, str]:
    if score <= 33.33:
        return "low", "risk_analysis_level_low"
    if score <= 66.66:
        return "moderate", "risk_analysis_level_moderate"
    return "high", "risk_analysis_level_high"

def calc_income_stability_risk(income_sources: List[Dict]) -> Tuple[float, str, Dict]:
    total_income = sum(s["value"] for s in income_sources)
    if total_income <= 0:
        return 80.0, "risk_analysis_reason_inc_none", {}
        
    num_sources = len(income_sources)
    salary_source = next((s for s in income_sources if s["id"] == "salary"), None)
    salary_val = salary_source["value"] if salary_source else 0.0
    non_salary_pct = ((total_income - salary_val) / total_income) * 100.0

    if num_sources >= 2 and non_salary_pct > 15.0:
        return 10.0, "risk_analysis_reason_inc_good", {}
    if num_sources >= 2:
        return 30.0, "risk_analysis_reason_inc_mod", {}
        
    return 60.0, "risk_analysis_reason_inc_high", {}
