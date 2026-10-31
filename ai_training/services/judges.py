"""The automatic judges. Code only: no judge asks a model. Every function returns a list of drop reasons; an empty list means "passed".
When in doubt the answer is a reason (throw it out)."""

from __future__ import annotations

from decimal import Decimal

from core.services.ai.domains import DATA_TOOLS
from core.services.ai.investigation import scope
from core.services.ai.investigation.actions import is_call_leak

from . import langcheck
from .textutil import appears, close, figures, pool_of

MODEL_ARG_TOOLS = ("app_data_models", "app_data_query")


def _expected_values(expected) -> list[Decimal]:
    return [Decimal(str(v)) for v in (expected or {}).get("values", [])]


def language_reasons(question: str, answer: str, declared: str = "") -> list[str]:
    """Same language as the question. French / German answers must be CONFIRMED by the app's own translation words (when in doubt, throw it out);
    English and Arabic answers only fail when the evidence says another language."""
    state = langcheck.verdict(question, answer, declared)
    if state == "other":
        return ["answer_in_other_language"]
    return ["language_not_confirmed"] if state == "unconfirmed" and declared in ("fr", "de") else []


def method_checks(question: str, answer: str, steps: list, reason: str, declared: str = "") -> list[str]:
    """(b) How the model worked: it looked at the user's own data first, used only data tools, and cited only what it read."""
    out = []
    if reason != "answered":
        out.append(f"not_answered:{reason}")
    if not str(answer or "").strip():
        out.append("empty_answer")
        return out
    if is_call_leak(answer) or "<think>" in answer or "</think>" in answer:
        out.append("leaked_tool_call_or_reasoning")
    tools = [s.get("tool") for s in steps]
    if not any(t in DATA_TOOLS for t in tools):
        out.append("did_not_look_at_data")
    if any(t not in DATA_TOOLS for t in tools):
        out.append("used_non_data_tool")
    for s in steps:
        args = s.get("arguments") or {}
        if s.get("tool") in MODEL_ARG_TOOLS and args.get("model") and scope.resolve_model(args["model"]) is None:
            out.append("unscoped_model")
        if str(s.get("result", "")).startswith('{"error"'):
            out.append("tool_error_in_run")
    pool = set().union(*(pool_of(s.get("result", "")) for s in steps)) if steps else set()
    pool |= {v for _, vs in figures(question, skip_dates=False) for v in vs}
    missing = [p for p, vs in figures(answer) if not appears(p, vs, pool)]
    if missing:
        out.append("figure_not_in_tool_results:" + ",".join(missing[:5]))
    return sorted(set(out + language_reasons(question, answer, declared)))


def data_check(answer: str, expected) -> list[str]:
    """(a) The numbers code computed from the owner's real rows must all be in the answer."""
    values = _expected_values(expected)
    if not values:
        return ["not_code_provable"]
    shown = figures(answer)
    return [f"wrong_or_missing_figure:{v}" for v in values if not any(close(v, r, p) for p, rs in shown for r in rs)]


def meta_of(expected) -> dict:
    return (expected or {}).get("meta") or {}


_YEAR = range(1900, 2101)


def clarify_checks(trace) -> list[str]:
    """Ambiguous question: the right answer asks what is meant instead of guessing. Proven by code: the answer ends in a question, gives no
    figure of its own (years and numbers already in the question excepted), leaks nothing, uses no non-data tool, and stays in the language.
    Whether the question it asks is a GOOD one is not provable by code."""
    answer, out = str(trace.answer or ""), []
    if trace.reason != "answered" or not answer.strip():
        return ["not_answered"]
    if is_call_leak(answer) or "<think>" in answer or "</think>" in answer:
        out.append("leaked_tool_call_or_reasoning")
    if "?" not in answer[-300:] and "؟" not in answer[-300:]:
        out.append("no_clarifying_question")
    allowed = {v for _, vs in figures(trace.question, skip_dates=False) for v in vs}
    guessed = [p for p, vs in figures(answer) if not any(v in allowed or (v == v.to_integral_value() and int(v) in _YEAR) for v in vs)]
    if guessed:
        out.append("guessed_instead_of_asking")
    if any(s.get("tool") not in DATA_TOOLS for s in trace.steps) or any(str(s.get("result", "")).startswith('{"error"') for s in trace.steps):
        out.append("used_non_data_tool_or_error")
    return sorted(set(out + language_reasons(trace.question, answer, meta_of(trace.expected).get("lang", ""))))


def judge_attempt(trace) -> list[str]:
    meta = meta_of(trace.expected)
    if meta.get("judge") == "clarify":
        return clarify_checks(trace)
    return method_checks(trace.question, trace.answer, trace.steps, trace.reason, meta.get("lang", "")) + data_check(trace.answer, trace.expected)


def repeat_check(attempts: list, expected=None) -> list[str]:
    """(c) The same question asked twice must give the same figures (and both runs must have passed on their own).
    With `expected` only the asked-for figures count: extras like a rate or a month number may differ between runs."""
    if len(attempts) < 2:
        return ["not_repeated"]
    if meta_of(expected).get("judge") == "clarify":
        return []   # each run already passed on its own; two different clarifying questions are both fine
    if _expected_values(expected):
        return [] if all(not data_check(a.answer, expected) for a in attempts) else ["not_repeatable"]
    first, *rest = [figures(a.answer) for a in attempts]
    for other in rest:
        if not all(any(close(a, b, p) for q, bs in other for b in bs) for p, avs in first for a in avs):
            return ["not_repeatable"]
        if not all(any(close(a, b, q) for p, avs in first for a in avs) for q, bs in other for b in bs):
            return ["not_repeatable"]
    return []
