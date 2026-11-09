"""Structural clean-up of a translated guide chunk (no word lists): Markdown emphasis a translator adds, a word written twice in
a row, and the count of numbered steps that a translation must not lose."""

from __future__ import annotations

import re

_CODE = re.compile(r"(```.*?```|`[^`\n]*`)", re.S)
_EMPHASIS = re.compile(r"(?<![*\w])\*(?![\s*])([^*\n]+?)(?<![\s*])\*(?![*\w])")   # *text* (not "**bold**", not a "* item" bullet)
_DOUBLED = re.compile(r"(?<![^\W\d_])([^\W\d_]{3,})[ \t]+\1(?![^\W\d_])", re.I)   # the same word twice in a row, letters only
_STEP = re.compile(r"^\s*\d+[.)]\s", re.M)   # \d also matches Arabic-Indic digits


def numbered_steps(text: str) -> int:
    return len(_STEP.findall(text))


def _outside_code(text: str, fix) -> str:
    return "".join(part if i % 2 else fix(part) for i, part in enumerate(_CODE.split(text)))


def strip_emphasis(text: str) -> str:
    """Single-asterisk emphasis left by a translator ("*word*") shows as literal asterisks in Word / PDF: the markers go, the
    text stays. Bold ("**x**"), bullets and code are untouched."""
    return _outside_code(text, lambda part: _EMPHASIS.sub(r"\1", part))


def drop_doubled_words(text: str) -> str:
    """"X X" becomes "X" in a text written in a non-Latin alphabet, where a word twice in a row is a translation slip. Only
    letters are compared (numbers, "(X) X" and "X, X" stay) and code is skipped. Not used for Latin-alphabet targets, where
    a doubled word can be correct ("nous nous")."""
    return _outside_code(text, lambda part: _DOUBLED.sub(r"\1", part))


def tidy_translation(text: str, non_latin: bool) -> str:
    text = strip_emphasis(text)
    return drop_doubled_words(text) if non_latin else text
