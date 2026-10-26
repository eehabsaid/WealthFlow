"""What a chat domain may touch and say, enforced in code (the model is also told, but never trusted).

Business: the user's own data only; no application structure, code or technical documentation.
App: how the application is built and works only; no financial data of the user.
A question outside the domain gets a short answer (app i18n, user's language) saying what the domain covers and which domain to switch to.
The model signals a question it cannot answer within its scope with the fixed token OUT_OF_SCOPE (not a phrase list)."""

from __future__ import annotations

import datetime
import re

from . import scope_text
from .domains import APP, BUSINESS

SENTINEL = "OUT_OF_SCOPE"
_NOTE = {
    BUSINESS: ("SCOPE: you answer only about the user's own financial and business data (accounts, balances, expenses, income, assets, "
               "forecasts), using the data and tools you are given. You have no information about the application's source code, "
               "architecture, database design or technical implementation, and no tool for them. "),
    APP: ("SCOPE: you answer only about the application itself: its features, screens and how it works. You have NO access to the "
          "user's personal financial data (balances, expenses, income, transactions, any figure of theirs) and never state any. "),
}
_RULES = ("Today is {today}: never present data for a date after today as if it existed, and never invent a value, a row or a "
          "day. If the question is outside your scope, or cannot be answered from what you were given, reply with exactly "
          f"{SENTINEL} and nothing else.")
_DATE = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b|\b(\d{1,2})[/.](\d{1,2})[/.](20\d\d)\b")
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def scope_note(domain: str, today: datetime.date | None = None) -> str:
    return _NOTE.get(domain, "") + _RULES.format(today=(today or datetime.date.today()).isoformat())


def no_info(question: str = "", domain: str = "") -> str:
    """The refusal in the user's language, from the app's i18n; with `domain` it names what the domain covers and where to switch."""
    return scope_text.refusal(scope_text.reply_language(question), domain)


def is_no_info(content: str) -> bool:
    return str(content or "").strip() in scope_text.all_refusals()


def is_out_of_scope(content: str) -> bool:
    return str(content or "").strip().strip("`*\"' .").upper().startswith(SENTINEL)


def apply_scope(messages: list[dict], domain: str) -> None:
    """The model's messages for a question in `domain`: the scope note and today's date; in the App domain the user's data block
    (everything after the context marker of the first system message) is removed so there is nothing to quote."""
    from core.views.ai_chat.chat_pipeline.retrieve import CONTEXT_MARKER

    if not messages:
        return
    if domain not in _NOTE:   # no strict domain: the model still gets today's date (it invented the rest of the month without it)
        messages.append({"role": "system", "content": _RULES.split(" If the question")[0].format(today=datetime.date.today().isoformat())})
        return
    first = messages[0]
    if domain == APP and first.get("role") == "system":
        first["content"] = str(first.get("content", "")).partition(CONTEXT_MARKER)[0].rstrip()
    messages.append({"role": "system", "content": scope_note(domain)})


def _dates(text: str) -> set[datetime.date]:
    out = set()
    for m in _DATE.finditer(str(text).translate(_ARABIC_DIGITS)):
        y, mo, d = (m.group(1), m.group(2), m.group(3)) if m.group(1) else (m.group(6), m.group(5), m.group(4))
        try:
            out.add(datetime.date(int(y), int(mo), int(d)))
        except ValueError:
            continue
    return out


def drop_future_rows(answer: str, question: str, evidence: str, today: datetime.date | None = None) -> tuple[str, int]:
    """The answer without the lines that carry a date after today which is neither in the question nor in the data the model was
    given (an invented row), and how many lines were dropped."""
    today = today or datetime.date.today()
    known = _dates(question) | _dates(evidence)
    kept, dropped = [], 0
    for line in str(answer).splitlines():
        if any(d > today and d not in known for d in _dates(line)):
            dropped += 1
            continue
        kept.append(line)
    return "\n".join(kept), dropped


def guard_answer(domain: str, content: str, question: str, evidence: str) -> str:
    """The answer after the domain rules: the sentinel and invented future rows become the short no-information answer; in the App
    domain any figure that is not in the question or the documentation is invented (it has no data), so the answer is replaced."""
    from core.views.ai_chat.chat_pipeline.grounding import ground_answer

    if is_out_of_scope(content):
        return no_info(question, domain)
    text, dropped = drop_future_rows(content, question, evidence)
    if dropped and len(text.strip()) < 0.3 * len(str(content).strip()):
        return no_info(question, domain)
    if domain == APP and not ground_answer(text, question, evidence).ok:
        return no_info(question, domain)
    return text if dropped else content
