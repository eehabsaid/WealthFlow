"""All question families of the 16 categories (the table-based kinds live in services/tables.py). Each module has train() and evaluate():
the kinds they produce are DISJOINT, so a test question is never a training question."""

from __future__ import annotations

from . import ambiguous, assets, budget, explain, income, overview, quality, spend, whatif

MODULES = (spend, whatif, explain, quality, income, assets, budget, overview, ambiguous)


def train_cases(user, langs, rng) -> list:
    return [c for m in MODULES for c in m.train(user, langs, rng)]


def eval_cases(user, langs, rng) -> list:
    return [c for m in MODULES for c in m.evaluate(user, langs, rng)]
