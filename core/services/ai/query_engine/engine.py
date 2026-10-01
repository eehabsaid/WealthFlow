"""Query engine entry point: question -> (route -> slots -> execute -> render) with 0 LLM calls,
or 1 short slot-filling call when the deterministic router is unclear. Anything else returns None and
the existing pipeline runs unchanged.

Every decision is written into `info` (the view puts it on the [AI-PIPELINE] `route` stage):
router status/confidence, chosen capability, slots, llm_calls, path (engine | llm_pipeline).
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from .registry import get_capability
from .render import render
from .slots import Routing, route
from .spec import QueryRequest

logger = logging.getLogger(__name__)
SETTING = "ai_direct_answers"


def is_enabled(user: Any) -> bool:
    from core.models import AppSettings

    return str(AppSettings.get(SETTING, "true", user=user)).strip().lower() not in ("false", "0", "no", "off")


def _category_lookup(user: Any):
    def lookup():
        from core.models import ExpenseCategory

        return list(ExpenseCategory.objects.filter(owner=user).values_list("name", flat=True))

    return lookup


def _audit(req: QueryRequest, text: str, started: float, llm_calls: int) -> dict[str, Any]:
    return {
        "tool": f"direct_answer_{req.capability}", "timestamp": datetime.now(timezone.utc).isoformat(), "status": "success",
        "duration_ms": int((time.monotonic() - started) * 1000), "arguments": {"search_query": text, "request": req.to_dict()},
        "step": 1, "direct_answer": True, "llm_calls": llm_calls,
    }


def answer(user: Any, text: str, *, provider: Any = None, understanding: Any = None, info: dict[str, Any] | None = None,
           elapsed_ms: int = 0) -> dict[str, Any] | None:
    """Return {content, tool_calls, sources} or None (fall through). Fills `info` either way."""
    started = time.monotonic()
    info = info if info is not None else {}
    info.setdefault("llm_calls", 0)
    info["path"] = "llm_pipeline"
    if user is None or not getattr(user, "is_authenticated", False):
        info["reason"] = "anonymous"
        return None
    if not is_enabled(user):
        info["reason"] = "kill_switch"
        return None
    routing: Routing = route(text, category_lookup=_category_lookup(user))
    info.update(routing.summary())
    if routing.status == "analytic" and routing.request is not None:
        info["facts_request"] = routing.request.to_dict()  # narrative path: model gets computed facts, not data
    if routing.status == "unclear" or (routing.status == "incomplete" and routing.needs_llm):
        from .llm_slots import fill_with_llm

        try:
            routing = fill_with_llm(provider, text, routing, info, user=user, elapsed_ms=elapsed_ms) or routing
        except Exception as exc:  # slot filling must never break chat
            logger.warning("LLM slot filling failed: %s", exc)
            info["llm_slots"] = f"error:{type(exc).__name__}"
        if routing.reason == "llm_slots":
            info.update({"status": "ready", "capability": routing.capability, "confidence": routing.confidence,
                         "slots": routing.request.to_dict(), "reason": "llm_slots"})
    if routing.status != "ready" or routing.request is None:
        return None
    cap = get_capability(routing.request.capability)
    if cap is None:
        return None
    try:
        content = render(cap.executor(user, routing.request))
    except Exception as exc:  # a data error must fall back to the model path, not 500
        logger.exception("query engine executor %s failed", cap.key)
        info.update({"path": "llm_pipeline", "reason": f"executor_error:{type(exc).__name__}"})
        return None
    info["path"] = "engine"
    info["answer_chars"] = len(content)
    return {"content": content, "tool_calls": [_audit(routing.request, text, started, info["llm_calls"])], "sources": list(cap.sources)}
