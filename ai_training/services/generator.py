"""Training questions from the live app: every table the Agent may read (tables.py) plus the 16-category families (families/), in English,
Arabic, French and German, simple to complex. Expected figures are computed by Django on the owner's real rows, never by a model.
Only questions code can prove are produced (a tie, an all-zero answer or an untranslatable label = no question). Near-duplicate wording is
removed, and anything that is a frozen TEST question (testset.py) is never a training question."""

from __future__ import annotations

import random

from core.services.ai.investigation import scope

from . import families, tables
from .case import norm_text
from .phrasing import LANGS

MAX_PER_TABLE = 24   # per table, a seeded sample of its kinds x languages: variety over volume


def dedupe(cases: list, blocked: set | None = None, *, test: bool = False) -> list:
    """One example per normalised question text; `blocked` = texts that must not appear (the frozen test questions)."""
    seen, out = set(blocked or ()), []
    for c in cases:
        text = norm_text(c.question)
        if text not in seen and c.key.startswith("eval:") == test:   # training keeps no test kind, the test keeps only test kinds
            seen.add(text)
            out.append(c)
    return out


def all_cases(user, seed: int | None = None, langs=LANGS) -> list:
    rng, cases = random.Random(seed), []
    for info in scope.catalog().values():
        found = tables.train_cases(info, user, rng, langs)
        rng.shuffle(found)
        cases += found[:MAX_PER_TABLE]
    cases += families.train_cases(user, langs, rng)
    return sorted(cases, key=lambda c: c.key)


def generate(user, *, limit: int = 0, seed: int | None = None, langs=LANGS, blocked: set | None = None) -> list:
    """All provable training cases for `user`; `limit` samples that many (seeded, repeatable)."""
    cases = dedupe(all_cases(user, seed, langs), blocked)
    if limit and len(cases) > limit:
        cases = sorted(random.Random(seed).sample(cases, limit), key=lambda c: c.key)
    return cases
