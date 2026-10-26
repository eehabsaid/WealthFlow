"""Heading discipline for the written guide, in code and not in word lists.

A screen the app documents WITHOUT tabs (doc_engine/inventory.json) has no sub-sections: a model that invents "Overview" /
"Main View" / "Steps" headings there makes the guide's structure change from run to run. Such a screen keeps only the headings
that name one of its documented dialogs (as dialog level, ####); every other sub-heading is dropped and its text stays.
STYLE_RULE tells the model the same thing and also asks for no "Purpose:" / "Steps:" labels, so the labels never differ
between sections (and never between languages: the translation has no label to translate)."""

from __future__ import annotations

import json
import re

from .compose_quality import norm

STYLE_RULE = ("\n\nGUIDE STYLE: write the purpose of a screen, tab or dialog as a plain paragraph and its steps as a numbered list, "
              "without a label such as 'Purpose' or 'Steps' in front of them. Use a sub-heading (###) only for a tab that is listed "
              "in the SCREEN data, and a #### heading only for a dialog that is listed there. A screen with no tabs listed has no ### headings.")
MIN_NAME = 4


def dialog_names(shown: dict) -> list[str]:
    """The names of the dialogs / actions of a screen's evidence (entries are dicts with a name, or plain strings)."""
    names = [d.get("name") if isinstance(d, dict) else d for d in shown.get("dialogs") or []]
    return [str(n).strip() for n in names if str(n or "").strip()]


def _is_dialog(name: str, dialogs: list[str]) -> bool:
    key = norm(name)
    return bool(key) and any(key == d or (len(key) >= MIN_NAME and len(d) >= MIN_NAME and (key in d or d in key)) for d in dialogs)


def drop_empty_headings(section: str) -> str:
    """A tab / dialog heading with no text and no sub-heading under it is dropped: an empty heading in the guide documents nothing
    (and a translator invents text for it)."""
    lines = section.splitlines()
    level = lambda line: len(line) - len(line.lstrip("#")) if line.startswith("#") else 0   # noqa: E731
    keep = []
    for i, line in enumerate(lines):
        if level(line) >= 3:
            rest = next((x for x in lines[i + 1:] if x.strip()), "")
            if not rest or 0 < level(rest) <= level(line):
                continue
        keep.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(keep)).rstrip()


def flatten_untabbed(section: str, unit: dict) -> str:
    """The section of a screen without tabs with only its chapter heading and its documented dialog headings."""
    if unit.get("tab_items"):
        return section
    dialogs = [k for k in (norm(d) for d in unit.get("dialogs") or []) if k]
    out: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") and not stripped.startswith(("# ", "## ")):
            name = stripped.lstrip("#").strip()
            if _is_dialog(name, dialogs):
                out.append(f"#### {name}")
            continue
        out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).rstrip()


def drop_intro(section: str) -> str:
    """The text before the first heading of a continuation part removed: a screen split in parts is one chapter that was introduced
    by its first part, and a model that writes a new introduction for the next part puts it (wrongly) under the last item of the
    part before."""
    lines = section.splitlines()
    first = next((i for i, line in enumerate(lines) if line.startswith("#")), None)
    return "\n".join(lines[first:]) if first else section


_LIST_LINE = re.compile(r"^\s*(\d+[.)]|[-*\u2022])\s")


def _documented_steps(unit: dict) -> dict[str, list[str]]:
    """{name: documented steps} of the tabs and dialogs of a unit's evidence."""
    try:
        shown = json.loads(unit.get("evidence") or "{}")
    except ValueError:
        return {}
    found: dict[str, list[str]] = {}
    for entry in [*shown.get("dialogs", []), *(d for t in shown.get("tabs", []) for d in t.get("dialogs", [])),
                  *({"name": t.get("name"), **(t.get("description") or {})} for t in shown.get("tabs", []))]:
        if isinstance(entry, dict) and entry.get("steps"):
            found.setdefault(norm(entry.get("name") or ""), [str(s) for s in entry["steps"]])
    found.pop("", None)
    return found


def ensure_steps(section: str, unit: dict) -> str:
    """A tab / dialog the app documents with steps gets them: the model sometimes writes the purpose only. The steps are the
    documented ones, appended as a numbered list under the heading that has no list at all."""
    steps = _documented_steps(unit)
    lines, out, i = section.splitlines(), [], 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        if line.startswith("###") and norm(line.lstrip("#")) in steps:
            j = i
            while j < len(lines) and not lines[j].startswith("#"):
                j += 1
            body = lines[i:j]
            out.extend(body)
            if not any(_LIST_LINE.match(x) for x in body):
                out.extend(["", *(f"{n}. {step}" for n, step in enumerate(steps[norm(line.lstrip("#"))], 1)), ""])
            i = j
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).rstrip()


def tidy(section: str, unit: dict) -> str:
    """One section as it goes into the guide: no invented sub-headings on a tab-less screen, no introduction repeated by a
    continuation part, no empty headings."""
    section = flatten_untabbed(section, unit)
    section = drop_intro(section) if unit.get("part", (1, 1))[0] > 1 else section
    return ensure_steps(drop_empty_headings(section), unit)
