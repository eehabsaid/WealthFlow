"""Structural quality gate for a guide written by the composer, whatever the model wrote and in whichever language.

Only the SHAPE of the text is judged (never words or phrases): a "(1/3)" part marker, a heading written twice, a chapter written
twice, a code block, a snake_case / ENV_VAR / file.py / --flag token (an internal, not something a user clicks) and a tab whose
text is thinner than the app's own documented text for it. Whatever fails is repaired from the documented text or dropped."""

from __future__ import annotations

import re

PART_MARKER = re.compile(r"\s*[\(\[]\s*\d+\s*/\s*\d+\s*[\)\]]\s*$")
FENCE = re.compile(r"```.*?```", re.S)
INTERNAL = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b|\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b|\S+\.py\b|(?<=\s)--[a-z][\w-]*|`[^`\n]*[_/\\.][^`\n]*`")
SENTENCE_END = re.compile(r"(?<=[.!?\u061f\u3002])\s+")
DUPLICATE_SHARE, DUPLICATE_MIN_WORDS = 0.85, 12   # a text of 12+ words that is 85% contained in an earlier one of its chapter
THIN_SHARE, MIN_DOCUMENTED = 0.5, 150   # a tab text shorter than half of its documented text (documented text of 150+ chars)


def clean_title(title: str) -> str:
    """A screen title without its part marker: "Financial Advisor (2/3)" -> "Financial Advisor"."""
    return PART_MARKER.sub("", str(title or "")).strip()


def norm(text: str) -> str:
    return "".join(ch for ch in str(text).lower().replace("&", "and") if ch.isalnum())


def _without_internals(line: str) -> str:
    """The line without the sentences that name an internal (a list item or heading carrying one is dropped whole)."""
    if not INTERNAL.search(line):
        return line
    if line.lstrip().startswith(("#", "-", "*")) or re.match(r"\s*\d+[.)]\s", line):
        return ""
    return " ".join(s for s in SENTENCE_END.split(line) if not INTERNAL.search(s))


def _chapters(markdown: str) -> list[str]:
    return [c for c in re.split(r"(?m)^(?=## )", markdown) if c.strip()]


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w{3,}", text.casefold()))


def _overlap(a: set[str], b: set[str]) -> float:
    """Share of the smaller word set found in the larger one (1.0: the same text, 0: nothing in common)."""
    small, big = (a, b) if len(a) <= len(b) else (b, a)
    return len(small & big) / len(small) if small else 1.0


def _drop_near_duplicates(chapter: str, protect: frozenset = frozenset()) -> str:
    """A sub-section or paragraph that says what an earlier one of the chapter already said (the model wrote a tab twice under two
    headings, or a later part repeated an earlier part) is dropped: judged on the words only, so it holds in every language."""
    kept_words: list[set[str]] = []
    out = []
    for part in re.split(r"(?m)^(?=### )", chapter):
        body = part.split("\n", 1)[1] if part.startswith("### ") and "\n" in part else part
        words = _words(body)
        real = any(p and p in norm(part.splitlines()[0]) for p in protect) if part.startswith("### ") else True
        if part.startswith("### ") and not real and len(words) >= DUPLICATE_MIN_WORDS and any(_overlap(words, w) >= DUPLICATE_SHARE for w in kept_words):
            continue
        paragraphs = []
        for para in re.split(r"\n{2,}", part):
            pw = _words(para)
            if len(pw) >= DUPLICATE_MIN_WORDS and not para.lstrip().startswith("#") and any(_overlap(pw, w) >= DUPLICATE_SHARE for w in kept_words):
                continue
            paragraphs.append(para)
            if len(pw) >= DUPLICATE_MIN_WORDS:
                kept_words.append(pw)
        out.append("\n\n".join(paragraphs))
    return "\n".join(p.rstrip() + "\n" if p.strip() else p for p in out).rstrip()


def _merge_repeated_headings(chapter: str) -> str:
    """A sub-heading written again inside one chapter is dropped (its text stays under the first one)."""
    seen: set[str] = set()
    out = []
    for line in chapter.splitlines():
        if line.startswith("### "):
            key = norm(line)
            if key in seen:
                continue
            seen.add(key)
        out.append(line)
    return "\n".join(out)


def _same_text(a: str, b: str) -> bool:
    """Two chapters with one title are one chapter written twice when most of the words of the shorter are in the longer."""
    words_a, words_b = set(re.findall(r"\w{3,}", a.casefold())), set(re.findall(r"\w{3,}", b.casefold()))
    small, big = (words_a, words_b) if len(words_a) <= len(words_b) else (words_b, words_a)
    return not small or len(small & big) / len(small) >= 0.6


def sanitize(markdown: str, english: bool = True, protect: frozenset = frozenset()) -> str:
    """The guide without part markers, code blocks, internals, repeated sub-headings and chapters written twice.
    Repeats are judged on the English text only: two different English titles may share one translation."""
    lines = []
    for line in FENCE.sub("", markdown).splitlines():
        if line.lstrip().startswith("#"):
            line = PART_MARKER.sub("", line)
        lines.append(_without_internals(line))
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    head, chapters = "", []
    for index, chapter in enumerate(_chapters(text)):
        if index == 0 and not chapter.startswith("## "):
            head = chapter.rstrip()
            continue
        chapters.append((_drop_near_duplicates(_merge_repeated_headings(chapter), protect) if english else chapter).rstrip())
    if english:
        first: dict[str, int] = {}
        unique: list[str] = []
        for chapter in chapters:       # the same chapter twice: the longer one stays, at the place of the first
            key = norm(chapter.splitlines()[0])
            if key not in first or not _same_text(chapter, unique[first[key]]):
                first.setdefault(key, len(unique))
                unique.append(chapter)
            elif len(chapter) > len(unique[first[key]]):
                unique[first[key]] = chapter
        chapters = unique
    return "\n\n".join(p for p in [head, *chapters] if p.strip()) + "\n"


def blocks(section: str) -> list[tuple[str, str]]:
    """[(name of the ### heading ("" before the first), the block's text)] of one section."""
    out: list[tuple[str, str]] = []
    for part in re.split(r"(?m)^(?=### )", section):
        out.append((norm(part.splitlines()[0].lstrip("# ")) if part.startswith("### ") else "", part))
    return out


def thin_tabs(unit: dict, section: str, documented) -> list[dict]:
    """The unit's tabs whose written block is much shorter than the app's own documented text for them (a model that wrote a
    one-line stub because it did not look the tab up). `documented(tab)` is the tab's documented Markdown."""
    written = dict(blocks(section))
    thin = []
    for tab in unit["tab_items"]:
        text = written.get(norm(tab.get("name")))
        have = len(documented(tab).split("\n", 1)[-1].strip())
        if text is not None and have >= MIN_DOCUMENTED and len(text.split("\n", 1)[-1].strip()) < THIN_SHARE * have:
            thin.append(tab)
    return thin


def replace_blocks(section: str, tabs: list[dict], documented) -> str:
    """The section with the ### block of each of these tabs replaced, in place, by the app's own documented text for it."""
    new = {norm(t.get("name")): documented(t) for t in tabs}
    return "\n\n".join(new.get(name, text).strip() for name, text in blocks(section)).strip()


def report(markdown: str) -> dict:
    """What is still wrong with a finished guide (all zero for a clean one); logged as [AI-GUIDE-QA] so a bad file can be explained."""
    chapters = _chapters(markdown)
    heads = [norm(PART_MARKER.sub("", c.splitlines()[0])) for c in chapters if c.startswith("## ")]
    return {
        "chapters": len(heads),
        "repeated_chapters": len(heads) - len(set(heads)),
        "repeated_sub_headings": sum(len(h) - len(set(h)) for h in ([norm(line) for line in c.splitlines() if line.startswith("### ")] for c in chapters)),
        "part_markers": sum(1 for line in markdown.splitlines() if line.startswith("#") and PART_MARKER.search(line)),
        "internals": len(INTERNAL.findall(FENCE.sub("", markdown))) + markdown.count("```") // 2,
    }
