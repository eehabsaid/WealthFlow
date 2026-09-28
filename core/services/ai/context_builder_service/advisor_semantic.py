"""Semantic matching of advisor services (backlog item 2).

Used only when nothing matched lexically and no business-data provider matched, i.e.
exactly where the builder would otherwise dump the 4 DEFAULT_CORE_SERVICES payloads.
Cost: one query embedding (shared LRU with provider scoring) + one-time embedding of the
11 descriptions (cached in-process). Any embedding failure returns [] -> old default."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

MAX_SEMANTIC_ADVISORS = 2
_PREFIX = "advisor:"  # keeps candidate-cache keys apart from provider keys

ADVISOR_SERVICE_DESCRIPTIONS: dict[str, str] = {
    "overview": "overall financial health score, net worth summary, key indicators and alerts",
    "cash_flow": "monthly cash flow forecast, income versus outgoings, upcoming bills and runway",
    "wealth_growth": "long term wealth growth projection, compounding, future net worth forecast",
    "portfolio_optimizer": "portfolio allocation across asset classes, diversification, rebalancing",
    "goal_planning": "saving goals, retirement, house or car purchase planning, target dates and required monthly savings",
    "risk_analysis": "financial risk exposure, emergency fund, concentration, debt and liquidity risk",
    "spending_intelligence": "spending habits, category trends, overspending, discretionary costs, ways to cut expenses",
    "opportunity_detection": "idle cash, better savings yield, certificate opportunities, ways to earn more on money",
    "performance": "historical investment performance, gains and losses, returns over time",
    "what_if_simulator": "what if simulation, hypothetical changes such as salary raise or windfall",
    "scenario_planner": "stress test scenarios such as recession, inflation, currency devaluation or job loss",
}


def semantic_advisor_matches(query: str, available: list[str]) -> list[str]:
    # Lazy imports: importing the providers/retrieval packages at module load pulls
    # core.services in a different order and creates an auth-services import cycle.
    from core.services.ai.providers.registry.scoring_semantic import select_semantic_matches
    from core.services.ai.retrieval import semantic_scores

    candidates = {_PREFIX + k: ADVISOR_SERVICE_DESCRIPTIONS[k] for k in available if k in ADVISOR_SERVICE_DESCRIPTIONS}
    if not (query or "").strip() or not candidates:
        return []
    try:
        scores = semantic_scores(query, candidates)
    except Exception as exc:
        logger.info("Semantic advisor matching skipped: %s", exc)
        return []
    if not scores:
        return []
    picked = select_semantic_matches(scores)
    ranked = sorted(picked, key=picked.get, reverse=True)[:MAX_SEMANTIC_ADVISORS]
    return [k[len(_PREFIX):] for k in ranked]
