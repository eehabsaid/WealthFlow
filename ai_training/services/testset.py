"""The frozen test set: questions from the live data that training never uses, covering every category and all four languages.

FROZEN = the list of question keys + wording is saved once in output/frozen_testset.json and reused by every run (delete the file to
make a new one). The expected figures are NOT frozen: they are recomputed from your live rows on every run, so they are always true; a
frozen question whose figure can no longer be computed (data changed) is reported as retired and left out for ALL models alike.
The file holds question wording only (it may contain your category / asset names) and stays local (output/ is git-ignored)."""

from __future__ import annotations

import json
import os
import random

from core.services.ai.investigation import scope

from . import families, tables
from .case import norm_text
from .generator import dedupe
from .phrasing import LANGS
from .taxonomy import CATEGORIES, REFERENCE

FILE = "frozen_testset.json"


def live_cases(user, seed: int) -> list:
    rng, cases = random.Random(seed), []
    for info in scope.catalog().values():
        cases += tables.eval_cases(info, user, rng, LANGS)
    cases += families.eval_cases(user, LANGS, rng)
    return sorted(dedupe(cases, test=True), key=lambda c: c.key)


def pick(cases: list, per_category: int, seed: int) -> list:
    """Per category a seeded sample, taken round-robin over the languages so every language is represented."""
    rng, out = random.Random(seed), []
    for cat in [c for c, _ in CATEGORIES] + [REFERENCE]:
        pool = [c for c in cases if c.meta.get("category") == cat]
        by_lang = {l: [c for c in pool if c.meta.get("lang") == l] for l in LANGS}
        for group in by_lang.values():
            rng.shuffle(group)
        chosen = []
        while len(chosen) < min(per_category, len(pool)):
            for l in LANGS:
                if by_lang[l] and len(chosen) < per_category:
                    chosen.append(by_lang[l].pop())
        out += chosen
    return sorted(out, key=lambda c: c.key)


def train_blocked(path: str) -> set:
    """Normalised texts of the frozen questions (so generator.generate can keep them out of training)."""
    try:
        with open(path, encoding="utf-8") as fh:
            return {norm_text(q["question"]) for q in json.load(fh)["questions"]}
    except (OSError, ValueError, KeyError):
        return set()


def build(user, *, out_dir: str, per_category: int, seed: int) -> tuple[list, list]:
    """(cases, retired keys). Freezes on the first call; later calls reuse the file."""
    path, live = os.path.join(out_dir, FILE), {c.key: c for c in live_cases(user, seed)}
    if not os.path.exists(path):
        chosen = pick(list(live.values()), per_category, seed)
        os.makedirs(out_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"seed": seed, "per_category": per_category, "questions": [{"key": c.key, "question": c.question} for c in chosen]}, fh, ensure_ascii=False, indent=1)
    with open(path, encoding="utf-8") as fh:
        frozen = json.load(fh)["questions"]
    cases = [live[q["key"]] for q in frozen if q["key"] in live and live[q["key"]].question == q["question"]]
    return cases, [q["key"] for q in frozen if q["key"] not in {c.key for c in cases}]
