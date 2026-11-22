"""Deterministic routing + slot filling: text -> Routing(QueryRequest, confidence, status).

Statuses: ready (execute) | analytic (needs the model; facts may be attached) | unclear (an
LLM slot call may help) | multi | unsupported_time | incomplete | blocked | none (not a lookup).
Anything that is not `ready` falls through to the existing pipeline unchanged.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Callable, Iterable

from .lexicon import ACTION, ANALYTIC, ANALYTIC_LOOKUP_BUDGET, APP_HELP, CHALLENGE, TIME_HINT, language, norm, rx
from .lexicon_fr_de import LANGS, fold, to_english
from .registry import get_capabilities
from .spec import Capability
from .timespec import parse_time
from .slots_fill import MAX_CHARS, Routing, build_request, score, KARATS, _first_hit, _match_names, fill_filters


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
    entity_q = q
    if out.lang in LANGS:   # fr / de: route on canonical English tokens, match the user's own names on the folded original
        entity_q = f"{to_english(q, out.lang)} {fold(q)}"
        q = to_english(q, out.lang)
    if previous and language(str(previous)) in LANGS:
        previous = to_english(norm(previous), language(str(previous)))
    if not q or len(raw) > MAX_CHARS:
        out.reason = "empty_or_too_long"
        return out
    if ACTION.search(q):
        return Routing(status="blocked", reason="action_request", lang=out.lang)
    if CHALLENGE.search(q):
        return Routing(status="blocked", reason="refers_to_previous_answer", lang=out.lang)
    if APP_HELP.search(q):
        return Routing(status="blocked", reason="app_help", lang=out.lang)
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
    req, problems = build_request(cap, q, time, out.lang, category_lookup, entity_q)
    out.request = req

    margin = top - second
    if second >= 2 and margin < 2:
        out.status, out.reason = "multi", "several_capabilities"
        return out
    ana_q = rx(cap.analytic_ok).sub(" ", q) if cap.analytic_ok else q   # words this capability answers by itself ("forecast")
    if (ANALYTIC_LOOKUP_BUDGET if cap.key == "budgets" else ANALYTIC).search(ana_q):
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


__all__ = [
    "MAX_CHARS",
    "Routing",
    "build_request",
    "score",
    "KARATS",
    "_first_hit",
    "_match_names",
    "fill_filters",
    "_FOLLOW_UP",
    "MAX_FOLLOW_UP_WORDS",
    "MIN_FOLLOW_UP_SCORE",
    "_follow_up",
    "route",
]
