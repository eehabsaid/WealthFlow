"""
Strips LaTeX math notation from AI response text.

The system prompt explicitly instructs the model never to use LaTeX
delimiters (see context_builder_service/prompt.py guardrail 3d), but local
models don't reliably follow that instruction — confirmed by a real
response still containing `\\( 141.237721 \\, \\text{USD} \\times 50.9 \\)`
after the guardrail was already in place. There is no LaTeX renderer
anywhere in this app's frontend, so any LaTeX that slips through would
otherwise display as raw broken text.

This is a deterministic, mechanical cleanup applied to every assistant
response as a safety net — not a replacement for the prompt guardrail
(which still helps reduce how often this triggers), but a guarantee that
even when the model ignores it, the user never sees raw LaTeX markup.
"""

from __future__ import annotations

import re

# Common LaTeX text/spacing commands -> plain text equivalents.
_LATEX_COMMAND_REPLACEMENTS = [
    (r"\\text\{([^}]*)\}", r"\1"),
    (r"\\times", "x"),
    (r"\\cdot", "x"),
    (r"\\approx", "~="),
    (r"\\div", "/"),
    (r"\\,", " "),
    (r"\\;", " "),
    (r"\\!", ""),
    (r"\\%", "%"),
]


def strip_latex(text: str) -> str:
    """Removes LaTeX math delimiters and common commands, leaving plain text."""
    if not text:
        return text

    cleaned = text

    for pattern, replacement in _LATEX_COMMAND_REPLACEMENTS:
        cleaned = re.sub(pattern, replacement, cleaned)

    # Delimiters themselves: \( \) \[ \] and $$ ... $$ / $ ... $ (bare, non-currency use).
    cleaned = re.sub(r"\\[()\[\]]", "", cleaned)
    cleaned = re.sub(r"\$\$([^$]*)\$\$", r"\1", cleaned)

    # Collapse any double spaces left behind by removed commands.
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)

    return cleaned
