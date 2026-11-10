"""Which files does the user want? The MODEL reads the whole message and the chat before it, so no exact wording is needed.

The word patterns in intent.py stay as the offline fallback and as a floor (an explicit "to excel" or ".pdf" is never lost), but they
cannot read a list ("word, pdf, and html"), a follow-up ("where is the HTML file?") or a complaint ("you forgot the HTML"). One short
English protocol question (reasoning off, one line back) answers those. It is asked only when the message contains a file-related
word (intent.might_want_file), so plain data questions keep their 0-model-call instant answers. The answer is stored for this request
(intent.set_resolved) and every later detect() / requested() call in the same request, whichever module makes it, sees it."""

from __future__ import annotations

import logging
import re
from typing import Any

from ai.services.exports.intent import clear_resolved, detect, has_file_word, might_want_file, set_resolved
from ai.services.exports.registry import all_formats

logger = logging.getLogger("ai.pipeline")
NONE_TOKEN, SAME_TOKEN, HISTORY_MESSAGES, HISTORY_CHARS, TIMEOUT_S, MAX_WORDS, MAX_REQUEST_CHARS = "NONE", "SAME", 4, 600, 30, 12, 700
_TOKEN = re.compile(r"[a-z]+")


def _prompt() -> str:
    formats = "; ".join(f"{f.key} = {f.label}" for f in all_formats())
    return ("You decide which downloadable files the user wants delivered with the answer to their LAST message. Read the whole message, "
            "in any language, and the earlier messages: a follow-up such as \"where is the HTML file?\", \"only export the HTML\" or "
            "\"you forgot the PDF\" refers to the file asked for earlier. A question about HOW to export, or a request that needs no file, "
            f"wants no file. Available formats: {formats}. Reply with ONLY the format keys, separated by commas, for every file wanted "
            f"now, or the single word {NONE_TOKEN}. No other words.")


REWRITE_PROMPT = ("Rewrite the user's LAST message as ONE complete, self-contained request. Keep every detail of the earlier messages it depends on "
                  "(what to create, its language, formats, scope) and everything the last message adds or changes. Write it in the language of the "
                  f"last message. Reply with ONLY the rewritten request, or the single word {SAME_TOKEN} when the last message is already complete by itself.")


def parse(raw: str | None, keys: set[str]) -> list[str] | None:
    """Format keys the reply names, [] for NONE, None when the reply is not a usable answer (then the word patterns decide)."""
    text = re.sub(r"<think>[\s\S]*?</think>", " ", str(raw or ""), flags=re.IGNORECASE).lower()
    words = _TOKEN.findall(text)
    if not words or len(words) > MAX_WORDS:
        return None
    found = list(dict.fromkeys(w for w in words if w in keys))
    if found:
        return found
    return [] if words == [NONE_TOKEN.lower()] else None


def _history(conversation: Any, user_msg: Any) -> list[dict]:
    try:
        rows = conversation.messages.filter(is_deleted=False).exclude(id=user_msg.id).order_by("-id")[:HISTORY_MESSAGES]
        return [{"role": m.role, "content": str(m.content or "")[:HISTORY_CHARS]} for m in reversed(list(rows)) if m.role in ("user", "assistant")]
    except Exception:  # noqa: BLE001 - the question is still answerable from the message alone
        return []


def _ask(provider: Any, messages: list, max_tokens: int) -> str:
    from ai.services.investigation.actions import strip_think

    try:
        res = provider.generate(messages, tools=None, temperature=0, max_tokens=max_tokens, reasoning="off", timeout=TIMEOUT_S)
        return strip_think(res.get("content")).strip() if isinstance(res, dict) and not res.get("error") else ""
    except Exception:  # noqa: BLE001 - provider down: the word patterns decide
        return ""


def restate_request(provider: Any, user_text: str, conversation: Any, user_msg: Any, formats: list) -> str:
    """A follow-up ("where is the HTML file?") alone loses what was asked earlier (the guide, its language): the model restates it as one complete
    request. Used only where the model works on the request anyway (Agent mode). The chat keeps the message as typed; SAME / empty / too long keeps it."""
    history = _history(conversation, user_msg)
    if not formats or not any(m["role"] == "user" for m in history):
        return user_text
    raw = _ask(provider, [{"role": "system", "content": REWRITE_PROMPT}, *history, {"role": "user", "content": f"LAST MESSAGE:\n{user_text}"}], 200)
    text = raw.strip().strip('"')
    logger.warning("[AI-PROTOCOL] question=full_request raw=%r", raw[:120])
    if not text or text.upper() == SAME_TOKEN or len(text) > MAX_REQUEST_CHARS or "\n\n" in text:
        return user_text
    set_resolved(text, [f.key for f in formats])   # the restated request names the same files
    return text


def resolve_file_intent(provider: Any, user_text: str, conversation: Any = None, user_msg: Any = None) -> list:
    """The formats wanted for this request (also stored for every detect() call of this request). The word patterns answer first and alone
    whenever they find a file ("export it to excel", "word, pdf, and html"): instant answers keep their 0 model calls. Only a message they
    read as "no file" that still contains a file-related word (a follow-up, a complaint, a question that mentions the file) goes to the
    model. Never raises: any failure keeps the word patterns."""
    from ai.services.exports.settings import exports_enabled

    clear_resolved()
    found = detect(user_text)
    if found or not (might_want_file(user_text) or has_file_word(user_text)) or not exports_enabled():   # no file-related word: 0 queries, 0 model calls
        return found
    history = _history(conversation, user_msg)
    if not might_want_file(user_text, tuple(m["content"] for m in history if m["role"] == "user")):
        return found
    keys = {f.key for f in all_formats()}
    raw = _ask(provider, [{"role": "system", "content": _prompt()}, *history, {"role": "user", "content": f"LAST MESSAGE:\n{user_text}"}], 40)
    answer = parse(raw, keys)
    logger.warning("[AI-PROTOCOL] question=file_intent raw=%r parsed=%s", raw[:80], "none" if answer is None else answer or NONE_TOKEN)
    if not answer:
        return found
    set_resolved(user_text, answer)
    return detect(user_text)
