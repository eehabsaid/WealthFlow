"""Stage 1 — Understand: intent / entities / scope from the raw user message.

Deterministic and LLM-free (a few regexes, ~1 ms) so it can run before anything
else, including the direct-answer shortcut. It does not fetch data and does not
touch retrieval scoring; its outputs are (a) the question_domain used to filter
tool schemas — identical to the previous inference — and (b) hints Validate uses
to decide whether checking the answer is worthwhile.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from core.services.ai.context_builder_service.constants import TOPIC_KEYWORD_MAP
from core.services.ai.period_parser import find_periods

from .grounding import extract_figures

_INTENTS: tuple[tuple[str, re.Pattern], ...] = (
    ("smalltalk", re.compile(
        r"^\s*(hi|hello|hey|thanks|thank you|good (morning|afternoon|evening)|salam|مرحبا|أهلا|اهلا|شكرا|شكراً)\b[\s!.,؟?]*$", re.I)),
    ("action_request", re.compile(r"^\s*(please\s+)?(add|create|delete|remove|update|edit|transfer|pay|record|change)\b", re.I)),
    ("comparison", re.compile(r"\b(compare|comparison|versus|vs|difference between)\b|قارن", re.I)),
    ("forecast", re.compile(r"\b(forecast|predict|projection|what if|scenario|simulate|will i)\b|توقع", re.I)),
    ("explanation", re.compile(r"\b(why|explain|how (does|do|is|come))\b|لماذا|اشرح", re.I)),
)
_TOPICS: dict[str, re.Pattern] = {
    "balance": re.compile(r"\b(balance|balances|bank|account|accounts)\b|رصيد|حساب", re.I),
    "certificates": re.compile(r"\b(certificate|certificates)\b|شهادة|شهادات", re.I),
    "expenses": re.compile(r"\b(expense|expenses|spend|spent|spending|bill|bills)\b|مصروف", re.I),
    "salary": re.compile(r"\b(salary|salaries|payslip|paycheck|income)\b|راتب|مرتب", re.I),
    "assets": re.compile(r"\b(asset|assets|property|real estate|gold|villa|apartment)\b|أصول|ذهب", re.I),
    "market": re.compile(r"\b(exchange rate|usd|dollar|gold price)\b|سعر", re.I),
    "debt": re.compile(r"\b(loan|loans|debt|credit card|installment|installments)\b|قرض", re.I),
    "goals": re.compile(r"\b(goal|goals|target|savings plan)\b|هدف", re.I),
}
_CURRENCY_RE = re.compile(r"\b(EGP|USD|EUR|GBP|SAR|AED|KWD|QAR)\b|جنيه|دولار", re.I)
_YEAR_RE = re.compile(r"\b(19[9]\d|20\d\d)\b")
_MULTI_PART_RE = re.compile(r"\b(and|also|then|as well as)\b|،|؛|\?.+\?", re.I)


@dataclass
class Understanding:
    intent: str
    question_domain: str
    topics: list[str] = field(default_factory=list)
    entities: dict[str, Any] = field(default_factory=dict)
    scope: dict[str, Any] = field(default_factory=dict)
    needs_data: bool = True
    complexity: str = "simple"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _language(text: str) -> str:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "unknown"
    arabic = sum(1 for c in letters if "\u0600" <= c <= "\u06ff")
    return "ar" if arabic / len(letters) > 0.5 else "en" if all(ord(c) < 0x250 for c in letters) else "other"


def understand(user_text: str, explicit_domain: str = "") -> Understanding:
    # Lazy: generation_pipeline lives in the view package that imports this one.
    from core.views.ai_chat.ai_chat_core_views.generation_pipeline import _infer_question_domain

    text = (user_text or "").strip()
    domain = (explicit_domain or "").strip() or _infer_question_domain(text)
    q = text.lower()

    intent = next((name for name, rx in _INTENTS if rx.search(text)), "")
    if not intent:
        intent = "app_structure" if domain == "app_features_architecture" else "data_lookup"

    topics = [k for k, rx in _TOPICS.items() if rx.search(text)]
    topics += [f"advisor:{k}" for k, kws in TOPIC_KEYWORD_MAP.items() if any(kw in q for kw in kws)]

    periods = [f"{y}-{m:02d}" for y, m in find_periods(text)]
    years = sorted({int(y) for y in _YEAR_RE.findall(text)})
    amounts = [f.raw for f in extract_figures(text) if f.value >= 100 and f.value not in years]
    entities = {
        "periods": periods, "years": years, "amounts": amounts,
        "currencies": sorted({m.group(0).upper() for m in _CURRENCY_RE.finditer(text)}),
        "quoted": re.findall(r"[\"“'‘]([^\"”'’]{2,40})[\"”'’]", text),
    }
    multi = bool(_MULTI_PART_RE.search(text)) or len(topics) > 2 or intent in ("comparison", "forecast")
    return Understanding(
        intent=intent, question_domain=domain, topics=topics, entities=entities,
        scope={"language": _language(text), "has_period": bool(periods or years), "chars": len(text)},
        needs_data=intent not in ("smalltalk", "app_structure"),
        complexity="multi_part" if multi else "simple",
    )
