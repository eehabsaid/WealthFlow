"""All question families of the 16 categories (the table-based kinds live in services/tables.py). Each module has train() and evaluate():
the kinds they produce are DISJOINT, so a test question is never a training question."""

from __future__ import annotations

from ai.packs import registry
from ai.training.services.families import ambiguous, balance, explain, quality, spend

ORDER = ("spend", "whatif", "explain", "quality", "income", "assets", "banking", "balance", "budget", "overview", "ambiguous")
_LOCAL = {"ambiguous": ambiguous, "balance": balance, "explain": explain, "quality": quality, "spend": spend}


def modules() -> list:
    """Generic families plus the ones the host packs registered (name -> module), in the fixed order."""
    extra = registry().training_families
    return [m for m in (_LOCAL.get(n) or extra.get(n) for n in ORDER) if m is not None]


def train_cases(user, langs, rng) -> list:
    return [c for m in modules() for c in m.train(user, langs, rng)]


def eval_cases(user, langs, rng) -> list:
    return [c for m in modules() for c in m.evaluate(user, langs, rng)]
