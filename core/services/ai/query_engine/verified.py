"""Verified data for the model path.

With Direct Answers OFF the engine is skipped, so the model used to see only the capped context summary and
had to guess the rest ("the remaining 7 entries are not listed"). This computes, with the SAME router and
executors the instant answers use, the exact table for the question and hands it to the model as ground
truth. No model call happens here; any problem returns None and the old path runs unchanged.
"""

from __future__ import annotations

import logging
from typing import Any

from .registry import get_capability
from .render import render
from .slots import route

logger = logging.getLogger(__name__)
MAX_CHARS = 16000
HEADER = ("VERIFIED DATA (exact rows computed by code from the user's own records, complete for the question "
          "asked). Present the answer from this table: keep every row and number exactly as written, do not "
          "summarise rows away, do not say rows are missing, do not recalculate. You may add one short comment.\n")


def verified_for_model(user: Any, text: str, *, previous: str = "", info: dict[str, Any] | None = None) -> str | None:
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    try:
        from .engine import _category_lookup

        routing = route(text, category_lookup=_category_lookup(user), previous=previous)
        if info is not None and routing.status == "analytic" and routing.request is not None:
            info.setdefault("facts_request", routing.request.to_dict())
        if routing.status != "ready" or routing.request is None:
            return None
        cap = get_capability(routing.request.capability)
        if cap is None:
            return None
        content = render(cap.executor(user, routing.request))
    except Exception as exc:  # best effort: the model path must never break because of this
        logger.warning("verified data failed: %s", exc)
        return None
    if not content:
        return None
    if len(content) > MAX_CHARS:
        content = content[:MAX_CHARS].rsplit("\n", 1)[0] + "\n(table cut here: it is longer than the model can read)"
    if info is not None:
        info["verified_data"] = {"capability": routing.request.capability, "chars": len(content)}
    return HEADER + content
