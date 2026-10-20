"""A translated guide follows the structure of its English source.

The English guide is clean (see compose_quality.sanitize), so its chapters and sub-headings are the truth about how many there
must be and in which order. A translation that has MORE chapters or sub-headings than its source wrote some twice (a model
repeating a heading at a chunk boundary, or a section twice): exactly the surplus is removed, repeats of a neighbour first. Two
different English titles that share one translation are never merged: with the same count nothing is touched, so the judgement
is by position in the source and never by the translated words."""

from __future__ import annotations

import re

from .compose_quality import norm

CHAPTER, SUB = re.compile(r"(?m)^(?=## )"), re.compile(r"(?m)^(?=### )")


def _words(text: str) -> set:
    return set(re.findall(r"\w{3,}", text.casefold()))


def _heads(parts: list[str]) -> list[str]:
    return [norm(p.splitlines()[0]) if p.strip() else "" for p in parts]


def _rank(parts: list[str], i: int) -> int:
    """How clearly parts[i] is a repeat: 0 = the same heading as the part before it, 1 = a heading seen earlier with the same text, 2 = same heading only."""
    heads = _heads(parts)
    if i > 0 and heads[i] == heads[i - 1]:
        return 0
    first = next((j for j in range(i) if heads[j] == heads[i]), None)
    if first is None:
        return 9
    a, b = _words(parts[first]), _words(parts[i])
    small, big = (a, b) if len(a) <= len(b) else (b, a)
    return 1 if not small or len(small & big) / len(small) >= 0.6 else 2


def _remove_surplus(parts: list[str], surplus: int, keep_longer: bool) -> list[str]:
    parts = list(parts)
    while surplus > 0:
        ranked = sorted((r, i) for i in range(len(parts)) if (r := _rank(parts, i)) < 9)
        if not ranked:
            break
        i = ranked[0][1]
        heads = _heads(parts)
        first = next(j for j in range(i) if heads[j] == heads[i]) if i else None
        if keep_longer and first is not None and len(parts[i]) > len(parts[first]):
            parts[first] = parts[i]      # the longer text stays, at the place of the first
        del parts[i]
        surplus -= 1
    return parts


def _trim_chapter(translated: str, source: str) -> str:
    t_parts, s_parts = SUB.split(translated), SUB.split(source)
    surplus = len(t_parts) - len(s_parts)
    if surplus <= 0:
        return translated
    first, rest = t_parts[0], t_parts[1:]
    return first + "".join(_remove_surplus(rest, surplus, keep_longer=False))


def align_to_source(source: str, translated: str) -> str:
    """`translated` without the chapters / sub-headings it holds beyond the English `source` (the same text when it holds none)."""
    s_chapters = [c for c in CHAPTER.split(source) if c.strip().startswith("## ")]
    t_all = [c for c in CHAPTER.split(translated) if c.strip()]
    head, t_chapters = (t_all[0], t_all[1:]) if t_all and not t_all[0].startswith("## ") else ("", t_all)
    kept = _remove_surplus(t_chapters, len(t_chapters) - len(s_chapters), keep_longer=True)
    if len(kept) == len(s_chapters):
        kept = [_trim_chapter(t, s) for t, s in zip(kept, s_chapters)]
    return "\n\n".join(p.rstrip() for p in [head, *kept] if p.strip()) + "\n"
