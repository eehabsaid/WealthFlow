"""Deterministic routing + slot filling: text -> Routing(QueryRequest, confidence, status).

Statuses: ready (execute) | analytic (needs the model; facts may be attached) | unclear (an
LLM slot call may help) | multi | unsupported_time | incomplete | blocked | none (not a lookup).
Anything that is not `ready` falls through to the existing pipeline unchanged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable, Iterable

from .lexicon import ACTION, ANALYTIC, ANALYTIC_LOOKUP_BUDGET, BUY_RE, KARAT_RE, MID_RE, N_RE, SELL_RE, TIME_HINT, find_currencies, language, norm, rx
from .registry import get_capabilities
from .spec import Capability, QueryRequest
from .timespec import TimeSpec, parse_time

MAX_CHARS = 600
KARATS = {"24", "22", "21", "18"}


@dataclass
class Routing:
    status: str = "none"
    reason: str = ""
    capability: str = ""
    confidence: float = 0.0
    request: QueryRequest | None = None
    scores: dict[str, int] = field(default_factory=dict)
    time: TimeSpec | None = None
    needs_llm: bool = False
    lang: str = "en"

    def summary(self) -> dict[str, Any]:
        return {"status": self.status, "reason": self.reason, "capability": self.capability,
                "confidence": round(self.confidence, 2), "scores": self.scores,
                "slots": self.request.to_dict() if self.request else {}, "time": self.time.to_dict() if self.time else {}}


def score(cap: Capability, q: str) -> int:
    return sum(w for pat, w in cap.terms if rx(pat).search(q))


def _first_hit(pairs: Iterable[tuple[str, tuple[str, ...]]], q: str) -> list[str]:
    return [name for name, pats in pairs if any(rx(p).search(q) for p in pats)]


def _match_names(names: Iterable[str], q: str) -> str:
    best = ""
    for name in names:
        n = norm(name)
        if n and len(n) >= 3 and rx(rf"(?<![\w]){re.escape(n)}(?![\w])").search(q) and len(n) > len(best):
            best = name
    return best


def fill_filters(cap: Capability, q: str, category_lookup: Callable[[], Iterable[str]] | None) -> dict[str, Any]:
    f: dict[str, Any] = {}
    if "currency" in cap.filters:
        codes = find_currencies(q)
        if codes:
            f["currencies"] = codes
    if "karat" in cap.filters:
        m = KARAT_RE.search(q)
        if m:
            f["karat"] = next(g for g in m.groups() if g)
    if "side" in cap.filters:
        buy, sell, mid = bool(BUY_RE.search(q)), bool(SELL_RE.search(q)), bool(MID_RE.search(q))
        side = "both" if buy and sell else "buy" if buy else "sell" if sell else "mid" if mid else ""
        if side:
            f["side"] = side
    if "category" in cap.filters and category_lookup is not None:
        hit = _match_names(category_lookup(), q)
        if hit:
            f["category"] = hit
    if {"bank", "asset_type"} & set(cap.filters):
        f["match_text"] = q  # executors match it against their own (owner-scoped) names
    return f


def build_request(cap: Capability, q: str, time: TimeSpec, lang: str, category_lookup=None) -> tuple[QueryRequest, list[str]]:
    """Slot filling for one chosen capability. Returns (request, problems)."""
    problems: list[str] = []
    metrics = [m.name for m in cap.metrics if m.terms and any(rx(p).search(q) for p in m.terms)]
    dims = _first_hit(cap.dimensions, q)
    if len(dims) > 1:
        problems.append("ambiguous_group_by")
    n_m = N_RE.search(q)
    req = QueryRequest(
        capability=cap.key, metric=metrics[0] if metrics else cap.default_metric, group_by=dims[0] if dims else "",
        periods=list(time.months), latest=time.kind == "latest",
        n=int(next(g for g in n_m.groups() if g)) if n_m else None,
        filters=fill_filters(cap, q, category_lookup), lang=lang,
    )
    if req.metric == "latest" and req.n is None:
        req.n = 5 if re.search(r"(expenses|transactions|purchases|payments|مصروفات|معاملات|عمليات|مشتريات)", q) else 1
    return req, problems


_FOLLOW_UP = re.compile(r"^\s*(?:and|also|then|what about|how about|ok(?:ay)?|so)\b|^\s*(?:و|طيب|وكمان|وكم|ماذا عن|وماذا عن|وبالنسبه)\s*|\?$|؟$")
MAX_FOLLOW_UP_WORDS = 9
MIN_FOLLOW_UP_SCORE = 3   # a follow-up only inherits the previous topic when that gives a CONFIDENT match


def _follow_up(q: str, caps: list[Capability], previous: str) -> tuple[str, Capability | None]:
    """"and how much I hold?" right after a gold-price question -> score it as "... gold holdings".
    Returns (augmented text, previous capability) or (q, None). Never invents a topic: needs a confident score."""
    if not previous or len(q.split()) > MAX_FOLLOW_UP_WORDS or not _FOLLOW_UP.search(q):
        return q, None
    pq = norm(previous)
    ranked = sorted(((score(c, pq), c) for c in caps), key=lambda x: -x[0])
    if ranked[0][0] <= 0 or not ranked[0][1].follow_subject:
        return q, None
    prev_cap = ranked[0][1]
    aug = f"{q} {prev_cap.follow_subject}"
    base = max(score(c, prev_cap.follow_subject) for c in caps)   # what the bare subject scores on its own
    best = max(score(c, aug) for c in caps)
    # the follow-up's OWN words must add evidence: "and thanks?" + the old topic must not become a question
    own_time = parse_time(q).kind != "none"                       # "what about last month?" adds a period of its own
    return (aug, prev_cap) if best >= MIN_FOLLOW_UP_SCORE and (best > base or own_time) else (q, None)


def route(text: str, *, category_lookup: Callable[[], Iterable[str]] | None = None, today: date | None = None,
          previous: str = "") -> Routing:
    q, raw = norm(text), str(text or "")
    out = Routing(lang=language(raw))
    if not q or len(raw) > MAX_CHARS:
        out.reason = "empty_or_too_long"
        return out
    if ACTION.search(q):
        return Routing(status="blocked", reason="action_request", lang=out.lang)
    caps = get_capabilities()
    ranked = sorted(((score(c, q), c) for c in caps), key=lambda x: -x[0])
    follow_of: Capability | None = None
    if ranked[0][0] <= 0:  # nothing matched on its own: maybe a short follow-up to the previous question
        q, follow_of = _follow_up(q, caps, previous)
        if follow_of is not None:
            ranked = sorted(((score(c, q), c) for c in caps), key=lambda x: -x[0])
            out.reason = f"follow_up_of:{follow_of.key}"
    out.scores = {c.key: s for s, c in ranked if s}
    top, cap = ranked[0]
    second = ranked[1][0] if len(ranked) > 1 else 0
    if top <= 0:
        out.reason = "no_capability"
        return out
    out.capability = cap.key
    time = parse_time(q, today)
    follow_form = bool(previous) and len(q.split()) <= MAX_FOLLOW_UP_WORDS and bool(_FOLLOW_UP.search(q))
    if (follow_of is not None or follow_form) and cap.time == "required" and not time.months and time.kind != "latest":
        prev_time = parse_time(norm(previous), today)  # "and for salary?" keeps the period of the previous question
        if prev_time.months:
            time = prev_time
            time.notes.append("period_from_previous_question")
    out.time = time
    req, problems = build_request(cap, q, time, out.lang, category_lookup)
    out.request = req

    margin = top - second
    if second >= 2 and margin < 2:
        out.status, out.reason = "multi", "several_capabilities"
        return out
    if (ANALYTIC_LOOKUP_BUDGET if cap.key == "budgets" else ANALYTIC).search(q):
        out.status, out.reason, out.confidence = "analytic", "needs_reasoning", 0.6
        return out
    if cap.time == "none" and time.months:
        out.status, out.reason = "unsupported_time", "history_not_supported"
        return out
    if margin == 1 or problems:
        out.status, out.needs_llm = "unclear", True
        out.reason = "ambiguous_capability" if margin == 1 else problems[0]
        out.confidence = 0.5
        return out
    if cap.time == "required" and not time.months and req.group_by not in cap.period_free_dims and not (time.kind == "latest" and req.metric in cap.latest_metrics):
        out.status, out.reason = "incomplete", "missing_period"
        out.needs_llm = bool(TIME_HINT.search(q))
        out.confidence = 0.4
        return out
    out.status = "ready"
    out.reason = out.reason if out.reason.startswith("follow_up_of:") else "deterministic"
    out.confidence = 0.95 if margin >= 3 else 0.85
    if follow_of is not None:
        out.confidence = min(out.confidence, 0.8)
    if time.notes:
        out.confidence -= 0.1
    return out
