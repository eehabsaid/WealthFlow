"""What may enter persistent memory: no secrets, no personal data, no guesses, no duplicates. Used by store.add for every entry (owner CLI and agent notes alike)."""

from __future__ import annotations

import re

SECRET_HINTS = ("password", "secret", "api_key", "apikey", "token", "bearer ", "passphrase", "private key")
GUESS_HINTS = ("probably", "maybe", "perhaps", "i think", "i guess", "i assume", "assuming", "might be", "not sure", "unverified", "unclear whether", "seems to", "presumably")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
LONG_DIGITS = re.compile(r"\b(?:\d[ -]?){9,}\d\b")
KEYLIKE = re.compile(r"\b(?:sk|pk|ghp|xox[a-z])[-_][A-Za-z0-9_-]{12,}|\b(?=[A-Za-z0-9_-]*[A-Z])(?=[A-Za-z0-9_-]*[a-z])(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{32,}\b")
WORD = re.compile(r"[a-z0-9_]+")
SIMILAR = 0.8


def refusal(text: str) -> str:
    """The reason an entry must not be stored, or ''."""
    low = text.lower()
    if any(h in low for h in SECRET_HINTS) or KEYLIKE.search(text):
        return "this looks like it contains a secret; memory never stores secrets"
    if any(h in low for h in GUESS_HINTS):
        return "memory keeps only verified facts: this reads as a guess or assumption"
    return ""


def redact(text: str) -> str:
    """Personal data is removed rather than refused: the rest of the finding is still useful."""
    return LONG_DIGITS.sub("[number]", EMAIL.sub("[email]", text))


def _words(text: str) -> set[str]:
    return set(WORD.findall(text.lower()))


def duplicate(body: str, existing: list[str]) -> bool:
    """Same text after normalising, or nearly the same words (Jaccard >= 0.8), against entries written as 'date: text'."""
    mine = _words(body)
    for row in existing:
        other = _words(row.split(": ", 1)[-1])
        if mine and other and len(mine & other) / len(mine | other) >= (SIMILAR if len(mine) >= 5 else 1.0):
            return True
    return False
