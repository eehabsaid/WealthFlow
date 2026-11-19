"""add_screenshots: the guide text in, the same text with live screenshots out (unchanged when anything is not possible)."""

from __future__ import annotations

import logging
import re

from ai.services.guide_shots import store
from ai.services.guide_shots.capture import capture
from ai.services.guide_shots.markers import insert
from ai.services.guide_shots.plan import targets
from ai.services.guide_shots.session import session_cookie
from ai.services.guide_shots.settings import blur, enabled

logger = logging.getLogger("ai.guide_shots")
DEFAULT_ORIGIN = "http://127.0.0.1:8000"
MIN_CHAPTERS = 3     # same test as the HTML guide: a guide has several "## " chapters
BUDGET_S = 600       # all screens together; pages that do not fit are simply left without an image


def is_guide(markdown: str) -> bool:
    return len(re.findall(r"(?m)^##\s", markdown or "")) >= MIN_CHAPTERS and "```" not in (markdown or "")


def add_screenshots(markdown: str, user, origin: str = "") -> str:
    if not markdown or user is None or not enabled() or not is_guide(markdown):
        return markdown
    blurred = blur()
    plan = targets(user, blurred)
    try:
        with session_cookie(user) as cookie:
            shots = capture(origin or DEFAULT_ORIGIN, cookie, plan, blurred, BUDGET_S)
    except Exception as err:   # noqa: BLE001 - screenshots are a bonus, the guide is already written
        logger.warning("guide screenshots skipped: %s", err)
        return markdown
    if not shots:
        return markdown
    for key, data in shots.items():
        store.save(user.pk, key, data)
    logger.info("[AI-GUIDE-SHOTS] %d of %d screens captured (blur=%s)", len(shots), len(plan), blurred)
    return insert(markdown, plan, set(shots))
