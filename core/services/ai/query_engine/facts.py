"""Item 5: for advice / why / comparison questions the model gets a SMALL block of code-computed facts
(exact figures, differences, shares), never raw data and never a request to do arithmetic."""

from __future__ import annotations

import logging
from typing import Any

from .registry import get_capability
from .render import render
from .spec import QueryRequest

logger = logging.getLogger(__name__)
MAX_CHARS = 900  # ~225 tokens ≈ 6 s of prefill at the measured 36.9 tok/s


def _line(name: str, f: dict[str, Any]) -> str:
    cur = f.get("currency", "")
    parts = []
    groups = f.get("groups")
    if isinstance(groups, dict) and groups:
        parts.append("; ".join(f"{k}: {v:,.2f}" for k, v in list(groups.items())[:12]))
        vals = list(groups.values())
        if len(vals) == 2 and vals[0]:
            parts.append(f"difference (second - first): {vals[1] - vals[0]:,.2f} ({(vals[1] - vals[0]) / vals[0] * 100:+.1f}%)")
    if "total" in f:
        parts.append(f"total: {float(f['total']):,.2f}")
    return f"- {name} [{cur}] " + " | ".join(parts) if parts else ""


def build_facts(user: Any, request: QueryRequest | dict[str, Any]) -> str | None:
    if isinstance(request, dict):
        request = QueryRequest(capability=request["capability"], metric=request.get("metric", ""), group_by=request.get("group_by", ""),
                               periods=[(int(p[:4]), int(p[5:7])) for p in request.get("periods", [])], latest=bool(request.get("latest")),
                               n=request.get("n"), filters=request.get("filters", {}), lang="en")
    cap = get_capability(request.capability)
    if cap is None or (cap.time == "required" and not request.periods):
        return None
    if request.metric in ("list", "latest", "top"):   # narrative wants totals, not rows
        request.metric = cap.default_metric
    if cap.key == "expenses" and len(request.periods) > 1:
        request.group_by = request.group_by or "month"
    try:
        result = cap.executor(user, request)
    except Exception as exc:  # facts are best-effort
        logger.warning("facts for %s failed: %s", cap.key, exc)
        return None
    text = _line(cap.label, result.facts) or render(result)
    return ("COMPUTED FACTS (exact, computed by code from the user's own data; quote them, never recalculate):\n" + text)[:MAX_CHARS]
