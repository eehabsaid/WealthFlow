"""The automatic judges. Code only: no judge asks a model. Every function returns a list of drop reasons; an empty list means "passed".
When in doubt the answer is a reason (throw it out)."""

from __future__ import annotations

from decimal import Decimal

from core.services.ai.domains import DATA_TOOLS
from core.services.ai.investigation import scope
from core.services.ai.investigation.actions import is_call_leak

from .textutil import appears, close, figures, pool_of, script_of

MODEL_ARG_TOOLS = ("app_data_models", "app_data_query")


def _expected_values(expected) -> list[Decimal]:
    return [Decimal(str(v)) for v in (expected or {}).get("values", [])]


def method_checks(question: str, answer: str, steps: list, reason: str) -> list[str]:
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
    if script_of(answer) != script_of(question):
        out.append("answer_in_other_language")
    return sorted(set(out))


def data_check(answer: str, expected) -> list[str]:
    """(a) The numbers code computed from the owner's real rows must all be in the answer."""
    values = _expected_values(expected)
    if not values:
        return ["not_code_provable"]
    shown = figures(answer)
    return [f"wrong_or_missing_figure:{v}" for v in values if not any(close(v, r, p) for p, rs in shown for r in rs)]


def judge_attempt(trace) -> list[str]:
    return method_checks(trace.question, trace.answer, trace.steps, trace.reason) + data_check(trace.answer, trace.expected)


def repeat_check(attempts: list) -> list[str]:
    """(c) The same question asked twice must give the same figures (and both runs must have passed on their own)."""
    if len(attempts) < 2:
        return ["not_repeated"]
    first, *rest = [figures(a.answer) for a in attempts]
    for other in rest:
        if not all(any(close(a, b, p) for q, bs in other for b in bs) for p, avs in first for a in avs):
            return ["not_repeatable"]
        if not all(any(close(a, b, q) for p, avs in first for a in avs) for q, bs in other for b in bs):
            return ["not_repeatable"]
    return []
