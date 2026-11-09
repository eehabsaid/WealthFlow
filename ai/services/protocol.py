"""The ONE fixed English protocol between the backend and the model (classifier questions and answers).

Nothing here is user-facing: the user never reads these prompts or tokens. Everything the user reads (guides, refusals,
progress, UI) comes from the app / i18n in the user's language. Tokens are protocol symbols, not language words: a reply
that is not exactly one of them (after lenient clean-up of case, markdown and punctuation) is "no usable answer" (None)
and the caller falls back to its structural evidence rule. Every raw reply is logged at WARNING (INFO is hidden)."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("core.ai.pipeline")

YES, NO = "YES", "NO"
ABOUT_APP_PROMPT = (
    f"Answer with exactly one word, {YES} or {NO} (in English, whatever language the request is in). Is the user asking for "
    "documentation of the application itself (a user guide, manual or description of its screens and features), rather than "
    "a report or analysis of their own financial data?")
_TOKEN = re.compile(r"[A-Za-z]+")


def parse_yes_no(raw: str | None) -> bool | None:
    """True for YES, False for NO, None for anything else (empty, gibberish, another language, a sentence)."""
    text = re.sub(r"<think>[\s\S]*?</think>", " ", str(raw or ""), flags=re.IGNORECASE)
    words = _TOKEN.findall(text)
    if not words or len(words) > 1:   # one word only: a sentence is not a protocol answer
        return None
    token = words[0].upper()
    return True if token == YES else False if token == NO else None


def log_reply(question: str, raw: str | None, parsed: bool | None) -> None:
    logger.warning("[AI-PROTOCOL] question=%s raw=%r parsed=%s", question, (raw or "")[:80], "none" if parsed is None else parsed)
