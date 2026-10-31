"""One generated question and what code proved about it. The tags (category, language, level, judge) travel inside `expected["meta"]`, so
a stored run always knows how it must be judged and which category it belongs to (no extra table column needed)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

LEVELS = ("simple", "intermediate", "complex")
JUDGES = ("figures", "clarify")


@dataclass
class Case:
    key: str
    question: str
    expected: dict = field(default_factory=dict)

    @property
    def meta(self) -> dict:
        return (self.expected or {}).get("meta") or {}


def make(key: str, question: str, values, *, category: str, lang: str = "en", level: str = "simple", judge: str = "figures") -> Case:
    """`values` = the figures code computed from the owner's rows (empty only for the "clarify" judge)."""
    return Case(key, question, {"values": list(values), "meta": {"category": category, "lang": lang, "level": level, "judge": judge}})


def norm_text(text: str) -> str:
    """Same question typed differently (case, spaces, punctuation) is the same training example."""
    return re.sub(r"[\W_]+", " ", str(text or "").lower()).strip()


def kind_of(case: Case) -> str:
    """Key without the language suffix and the phrasing number: the 'intent + target' a question belongs to."""
    return case.key.split("|")[0]
