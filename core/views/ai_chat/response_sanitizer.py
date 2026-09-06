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


_ROLE_LABELS = {"assistant", "user", "system", "tool"}


def strip_leaked_control_tokens(text: str, valid_tool_names: set[str] | None = None) -> str:
    """
    Strips leaked raw tool-name / chat-role-label lines that some local-model
    outputs prepend before the real answer, e.g.:
        "query_application_data\\nassistant\\n\\nBased on the provided data..."
    Only strips lines that are EXACTLY a registered tool name or a bare role
    label (nothing else on the line) — never touches ordinary prose, so a
    real answer that happens to mention a tool name mid-sentence is untouched.
    """
    if not text:
        return text

    valid_tool_names = valid_tool_names or set()
    lines = text.split("\n")
    idx = 0
    while idx < len(lines):
        stripped = lines[idx].strip()
        if stripped and (stripped in valid_tool_names or stripped.lower() in _ROLE_LABELS):
            idx += 1
            continue
        if stripped == "":
            idx += 1
            continue
        break

    return "\n".join(lines[idx:]).lstrip("\n")


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
