"""Entity grounding (backlog item 6): months and currency codes named in an answer must exist in
the evidence (or the question). Deterministic, no LLM, ~ms — complements numeric grounding.py.

Deliberately narrow to avoid false alarms: months come from explicit mentions only
(find_periods), and currency codes are only checked when the evidence itself uses ISO codes.
"""

from __future__ import annotations

import re

from core.services.ai.period_parser import find_periods

from .coverage import period_in_context

_CUR_RE = re.compile(r"\b(EGP|USD|EUR|GBP|SAR|AED|KWD|QAR)\b")


def _periods(text: str) -> set[str]:
    return {f"{y}-{m:02d}" for y, m in find_periods(text)}


def check_entities(answer: str, question: str, evidence: str) -> tuple[int, list[str]]:
    """(entities_checked, ungrounded labels)."""
    checked, bad = 0, []
    asked = _periods(question)
    known = _periods(evidence)
    # "the paid salaries for 2026": the whole year was asked for, so naming any of its months is not a new claim
    asked_years = {y for y in re.findall(r"\b(20\d{2})\b", question or "")} if not asked else set()
    for p in sorted(_periods(answer) - asked):
        if p[:4] in asked_years:
            continue
        checked += 1
        if p not in known and not period_in_context(evidence, p):
            bad.append(f"month {p}")
    ev_codes = set(_CUR_RE.findall(evidence))
    if ev_codes:
        asked_codes = set(_CUR_RE.findall(question.upper()))
        for code in sorted(set(_CUR_RE.findall(answer)) - asked_codes):
            checked += 1
            if code not in ev_codes:
                bad.append(f"currency {code}")
    return checked, bad
