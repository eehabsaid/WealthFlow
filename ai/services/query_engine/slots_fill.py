"""Routing result, scoring and slot filling for the query engine."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from .lexicon import BUY_RE, KARAT_RE, MID_RE, N_RE, SELL_RE, find_currencies, norm, rx
from .lexicon_fr_de import fold
from .spec import Capability, QueryRequest
from .timespec import TimeSpec


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
    q = fold(q)   # accent-insensitive: a "Café" category matches "cafe"
    for name in names:
        n = fold(norm(name))
        if n and len(n) >= 3 and rx(rf"(?<![\w]){re.escape(n)}(?![\w])").search(q) and len(n) > len(best):
            best = name
    return best


def fill_filters(cap: Capability, q: str, category_lookup: Callable[[], Iterable[str]] | None, entity_q: str | None = None) -> dict[str, Any]:
    """`q` is the routing text; `entity_q` (fr/de: translated + accent-folded original) is where the user's own names are matched."""
    entity_q = q if entity_q is None else entity_q
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
        hit = _match_names(category_lookup(), entity_q)
        if hit:
            f["category"] = hit
    if "target" in cap.filters:
        f["target_text"] = q  # the executor reads "6 months" out of it
    if {"bank", "asset_type"} & set(cap.filters):
        f["match_text"] = entity_q  # executors match it against their own (owner-scoped) names
    return f


def build_request(cap: Capability, q: str, time: TimeSpec, lang: str, category_lookup=None, entity_q: str | None = None) -> tuple[QueryRequest, list[str]]:
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
        filters=fill_filters(cap, q, category_lookup, entity_q), lang=lang,
    )
    if req.metric == "latest" and req.n is None:
        req.n = 5 if re.search(r"(expenses|transactions|purchases|payments|مصروفات|معاملات|عمليات|مشتريات)", q) else 1
    return req, problems
