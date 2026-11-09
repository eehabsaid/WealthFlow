"""Chat stage 1a (second half): "translate it to Arabic" / "now in French" turns the PREVIOUS answer into a new answer written in that language,
with download links (the original answer stays as it is).

Nothing is decided by phrase lists: a short message after a real answer is put to the model as one YES/NO question ("is this a request to
translate the earlier answer?") and one language-name question; the translation itself is the guide's chunk-by-chunk translator
(investigation/compose_translate.py: rejects cut-off, empty, unchanged, still-English text and lost headings, retries in smaller pieces).
Code then checks what the model cannot be trusted with: every number of the original must still be in the translation, and no piece may
have stayed untranslated. Otherwise NOTHING is delivered but a plain note, never a half-translated or altered answer."""

from __future__ import annotations

import re
import time
from types import SimpleNamespace
from typing import Any

from ai.services.exports import default_formats, detect as detect_export_formats, previous_answer
from ai.services.exports.document import strip_export_lines
from ai.services.investigation.compose import _ask
from ai.services.investigation.compose_translate import translate_markdown, uses_latin_script
from ai.services.protocol import log_reply, parse_yes_no
from ai.services.query_engine import route as route_question
from ai.services.query_engine.labels import t as label
from ai.services.query_engine.lexicon import language as language_of

from ai.views.ai_chat.ai_chat_core_views.response_finalizer import finalize_success

TRANSLATE_TOOL = "translate_followup"
MAX_WORDS, MIN_SOURCE_CHARS = 12, 200   # a follow-up is short, and only a real answer is worth translating
_IS_TRANSLATION = ("Answer YES or NO only. Is the request below asking to translate the previous answer or document into another language? "
                   "Answer NO when it is a new question or asks for anything else.")
_NAME = ("Answer with one word only: the English name of the language the request below asks to translate into (for example English, Arabic, "
         "French, German). Reply NONE when it names no language.")
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_NUMBER = re.compile(r"\d[\d.,٫٬]*\d|\d")


def numbers_of(text: str) -> set[str]:
    """The numbers of a text as plain digit strings (Arabic-Indic digits and separators folded), so 1,234.50 and ١٬٢٣٤٫٥٠ compare equal."""
    folded = str(text or "").translate(_DIGITS).replace("٬", ",").replace("٫", ".")
    return {re.sub(r"[.,]", "", n) for n in _NUMBER.findall(folded)}


def numbers_kept(source: str, translated: str) -> bool:
    return numbers_of(source) <= numbers_of(translated)


def language_name(ask, user_text: str) -> str:
    """The language to translate into (English name) or "" when none is named / the answer is not a language name."""
    word = ask(_NAME, user_text, 0).strip().strip(".\"'`*").split("\n")[0].strip()
    if not word or len(word) > 24 or word.upper() == "NONE" or not all(ch.isalpha() or ch in " -" for ch in word):
        return ""
    return word


def translate_followup_response(*, provider: Any, cache_mgr: Any, progress_key: Any, conversation: Any, user_msg: Any, user_text: str,
                                request: Any, trace: Any, understanding: Any = None):
    """The JsonResponse for a translate follow-up, or None when the message is anything else (the normal pipeline goes on)."""
    target = previous_answer(conversation, user_msg.id)
    source = strip_export_lines(target.content).strip() if target else ""
    if len(source) < MIN_SOURCE_CHARS or len(user_text.split()) > MAX_WORDS:
        return None
    previous_text = conversation.messages.filter(role="user", is_deleted=False).exclude(id=user_msg.id).order_by("-id").values_list("content", flat=True).first() or ""
    if getattr(route_question(user_text, previous=previous_text), "status", "") != "none" or list(getattr(understanding, "topics", None) or []):
        return None   # a question the instant-answer engine or the topic detector knows is never a translation: no model call is spent on it
    from ai.services.agent.settings import document_budget_s

    deadline, out = time.monotonic() + document_budget_s(), SimpleNamespace(llm_calls=0, cut_off=False, cancelled=False, cancel_check=None)

    def ask(system: str, content: str, temperature: float = 0.2) -> str:
        return _ask(provider, out, system, content, deadline, temperature, reasoning="off")

    raw = ask(_IS_TRANSLATION, user_text, 0)
    asked = parse_yes_no(raw)
    log_reply("translate_followup", raw, asked)
    language = language_name(ask, user_text) if asked else ""
    if not language:
        return None
    trace.skip_remaining(TRANSLATE_TOOL)
    non_latin, stats = not uses_latin_script(ask, language), {}

    def progress(n, total, _language, started):
        from ai.services.investigation.loop_helpers import publish_legacy

        publish_legacy(request.user, conversation.id, n, total, "document_section", f"Translating into {language}", started)

    translated = translate_markdown(ask, lambda: bool(out.cut_off), source, language, deadline, progress, non_latin, stats)
    complete = bool(translated.strip()) and not stats.get("kept_english") and numbers_kept(source, translated)
    trace.log_summary()
    formats = detect_export_formats(user_text) or default_formats()
    call = {"tool": TRANSLATE_TOOL, "target_message_id": target.id, "language": language, "complete": complete, "formats": [f.key for f in formats]}
    return finalize_success(
        cache_mgr, progress_key, conversation, user_msg, user_text,
        translated if complete else label(language_of(user_text), "translate_incomplete", language=language),
        [call], [], request, offer_export=complete,
    )
