"""ONE short LLM call that turns an unclear question into a typed QueryRequest (JSON), with a wall-clock budget.

Only used when deterministic routing is unclear (see slots.route). ~300 tokens in / ~40 out. The reply is
validated against the capability declarations; anything invalid returns None and the existing pipeline runs.
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from .registry import catalogue_for_prompt, get_capability
from .slots import KARATS, Routing
from .spec import QueryRequest

_PERIOD = re.compile(r"^(19|20)\d\d-(0[1-9]|1[0-2])$")
_SYSTEM = (
    "Convert the user's finance question into ONE JSON object and nothing else.\nCapabilities:\n{catalogue}\n"
    'Keys: capability, metric, group_by, periods (list of "YYYY-MM"), latest (true/false), '
    'filters (currencies: list of ISO codes, karat: "24|22|21|18", side: "buy|sell", category: text).\n'
    'Use "" or [] when not stated. If it is not a plain data lookup (advice, why, compare, forecast) return {{"capability": ""}}.\n'
    "Today: {today}."
)
PROMPT_TOKENS_EST, OUTPUT_TOKENS_EST = 300, 40


def estimate_seconds(prompt_tokens: int = PROMPT_TOKENS_EST, out_tokens: int = OUTPUT_TOKENS_EST, user: Any = None) -> float:
    """COMPUTED, not measured: tokens / throughput. Defaults are the throughput measured on the dev machine
    (prompt 36.9 tok/s, decode 1.67 tok/s); override with AppSettings ai_prompt_tps / ai_decode_tps."""
    from core.models import AppSettings

    def num(key: str, default: float) -> float:
        try:
            return max(float(AppSettings.get(key, str(default), user=user)), 0.1)
        except (TypeError, ValueError):
            return default

    return prompt_tokens / num("ai_prompt_tps", 36.9) + out_tokens / num("ai_decode_tps", 1.67)


def request_from_json(obj: Any, lang: str) -> QueryRequest | None:
    """Validate model output against declarations. Never trusts a field it cannot verify."""
    if not isinstance(obj, dict):
        return None
    cap = get_capability(str(obj.get("capability") or ""))
    if cap is None:
        return None
    metric = str(obj.get("metric") or "")
    group = str(obj.get("group_by") or "")
    periods = []
    for p in obj.get("periods") or []:
        if not isinstance(p, str) or not _PERIOD.match(p):
            return None
        periods.append((int(p[:4]), int(p[5:7])))
    periods = sorted(set(periods))[:36]
    latest = bool(obj.get("latest"))
    raw = obj.get("filters") if isinstance(obj.get("filters"), dict) else {}
    filters: dict[str, Any] = {}
    if "currency" in cap.filters and isinstance(raw.get("currencies"), list):
        codes = [str(c).upper() for c in raw["currencies"] if re.fullmatch(r"[A-Za-z]{3}", str(c))]
        if codes:
            filters["currencies"] = codes
    if "karat" in cap.filters and str(raw.get("karat") or "") in KARATS:
        filters["karat"] = str(raw["karat"])
    if "side" in cap.filters and raw.get("side") in ("buy", "sell", "mid", "both"):
        filters["side"] = raw["side"]
    if "category" in cap.filters and isinstance(raw.get("category"), str) and raw["category"].strip():
        filters["category"] = raw["category"].strip()[:60]
    if cap.time == "none" and periods:
        return None
    if cap.time == "required" and not periods and not (latest and (metric or cap.default_metric) in cap.latest_metrics):
        return None
    return QueryRequest(
        capability=cap.key, metric=metric if metric in cap.metric_names() else cap.default_metric,
        group_by=group if group in cap.dimension_names() else "", periods=periods, latest=latest and not periods,
        filters=filters, lang=lang,
    )


def fill_with_llm(provider: Any, text: str, routing: Routing, info: dict[str, Any], user: Any = None, elapsed_ms: int = 0) -> Routing | None:
    from core.models import AppSettings

    if str(AppSettings.get("ai_query_llm_slots", "true", user=user)).strip().lower() in ("false", "0", "no"):
        info["llm_slots"] = "disabled"
        return None
    try:
        budget = float(AppSettings.get("ai_query_llm_budget_s", "45", user=user))
    except (TypeError, ValueError):
        budget = 45.0
    est = estimate_seconds(user=user)
    if provider is None or est + elapsed_ms / 1000 > budget:
        info["llm_slots"] = f"skipped_budget(est={est:.0f}s,budget={budget:.0f}s)" if provider is not None else "no_provider"
        return None
    system = _SYSTEM.format(catalogue=catalogue_for_prompt(), today=date.today().isoformat())
    res = provider.generate([{"role": "system", "content": system}, {"role": "user", "content": text[:400]}],
                            tools=None, max_tokens=90, temperature=0.01, timeout=int(budget))
    info["llm_calls"] = 1
    content = str((res or {}).get("content") or "") if isinstance(res, dict) else ""
    m = re.search(r"\{.*\}", content, re.S)
    try:
        req = request_from_json(json.loads(m.group(0)) if m else None, routing.lang)
    except (ValueError, TypeError):
        req = None
    if req is None:
        info["llm_slots"] = "invalid_or_not_a_lookup"
        return None
    info["llm_slots"] = "ok"
    return Routing(status="ready", reason="llm_slots", capability=req.capability, confidence=0.7, request=req,
                   scores=routing.scores, time=routing.time, lang=routing.lang)
