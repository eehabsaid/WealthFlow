"""Shared helpers of the question families: the owner's scoped rows (the same scope the AI tools use), money rounding, and `expand`, which
turns one proven fact into questions in every language and several phrasings."""

from __future__ import annotations

import random
from decimal import ROUND_HALF_UP, Decimal

from core.services.ai.investigation import scope

from . import phrasing
from .case import Case, make

PHRASINGS_EN = 2        # English gets all its phrasings, every other language one (seeded choice): variety without piling up near-copies


def rows(user, name: str):
    """The user's own rows of one table, via the AI's own scope catalog (None when the table is not queryable)."""
    info = scope.catalog().get(name)
    return scope.scoped_queryset(info, user) if info else None


def dec(value) -> Decimal:
    return Decimal(str(value or 0))


def money(value) -> str:
    return str(dec(value).quantize(Decimal("0.01"), ROUND_HALF_UP))


def percent(part, whole) -> str | None:
    return money(dec(part) * 100 / dec(whole)) if dec(whole) else None


def nonzero(values) -> bool:
    """A question whose every figure is zero proves nothing (any answer containing 0 would pass): skipped."""
    return any(dec(v) != 0 for v in values)


def expand(base: str, intent: str, rng: random.Random, langs, values, slots, *, category: str, level: str = "intermediate",
           judge: str = "figures", prefix: str = "") -> list[Case]:
    """`slots(lang)` -> the frame's slots in that language (a None slot = no question). English keeps its first phrasing's plain key."""
    out = []
    for lang in langs:
        count = phrasing.variants(intent, lang)
        picks = range(min(count, PHRASINGS_EN)) if lang == "en" else ([rng.randrange(count)] if count else [])
        for v in picks:
            text = phrasing.say(intent, lang, v, **(slots(lang) or {"x": None}))
            if text:
                key = prefix + base if (lang == "en" and v == 0) else f"{prefix}{base}|{lang}{v}"
                out.append(make(key, text, values, category=category, lang=lang, level=level, judge=judge))
    return out


def unique_names(queryset, field: str = "name") -> dict:
    """{id: name} for rows whose name is filled and appears only once (a question naming one of two same-named things is ambiguous)."""
    names = {}
    for pk, name in queryset.values_list("pk", field):
        names.setdefault(str(name or "").strip(), []).append(pk)
    return {ids[0]: n for n, ids in names.items() if n and len(ids) == 1}
