# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
from typing import Dict, List, Any

def _to_float(value) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def converted_egp(amount: float, currency_code: str, rates: Dict[str, float]) -> float:
    """Amount in the user's default currency. `rates` maps code -> value of one
    unit in that default currency (the default itself is 1); a blank code is
    treated as already being in the default currency."""
    code = str(currency_code or "").upper()
    if not code:
        return amount
    return amount * _to_float(rates.get(code))

def gold_trend_change(history: List[Any], window_days: int) -> float:
    if len(history) < 2:
        return 0.0

    latest = _to_float(history[0].carat_21k)
    idx = min(len(history) - 1, max(window_days - 1, 1))
    baseline = _to_float(history[idx].carat_21k)
    if baseline <= 0:
        return 0.0

    return ((latest - baseline) / baseline) * 100

def append_unique(items: List[str], value: str) -> None:
    if value not in items:
        items.append(value)
