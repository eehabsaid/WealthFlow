"""Heading discipline for the written guide, in code and not in word lists.

A screen the app documents WITHOUT tabs (doc_engine/inventory.json) has no sub-sections: a model that invents "Overview" /
"Main View" / "Steps" headings there makes the guide's structure change from run to run. Such a screen keeps only the headings
that name one of its documented dialogs (as dialog level, ####); every other sub-heading is dropped and its text stays.
STYLE_RULE tells the model the same thing and also asks for no "Purpose:" / "Steps:" labels, so the labels never differ
between sections (and never between languages: the translation has no label to translate)."""

from __future__ import annotations

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
