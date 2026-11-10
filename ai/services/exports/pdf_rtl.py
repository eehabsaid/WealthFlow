"""Right-to-left text for ReportLab: wrap FIRST (on the logical text), then reshape + bidi PER LINE.

ReportLab wraps whatever string it is given. Reshaping/bidi of a whole paragraph before that makes the wrapped lines come out in
reverse order. Here the lines are chosen on the logical words (measured with their reshaped width), each line is reordered on its own
with an RTL base direction (so a Latin term in parentheses keeps its order), and the lines are joined with <br/>.
"""

from __future__ import annotations

import re
from xml.sax.saxutils import escape

from reportlab.pdfbase.pdfmetrics import stringWidth

_WORD = re.compile(r"\S+")


def visual(text: str) -> str:
    """One line in visual order: Arabic letters joined, base direction right-to-left."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        return get_display(arabic_reshaper.reshape(text), base_dir="R")
    except Exception:  # noqa: BLE001 - never lose the text
        return text


def _shaped_width(word: str, face: str, size: float) -> float:
    try:
        import arabic_reshaper

        word = arabic_reshaper.reshape(word)
    except Exception:  # noqa: BLE001
        pass
    return stringWidth(word, face, size)


def _tokens(runs: list[tuple[str, bool]], bold_all: bool) -> list[tuple[str, bool]]:
    return [(m.group(0), bold or bold_all) for text, bold in runs for m in _WORD.finditer(text)]


def wrap_lines(runs: list[tuple[str, bool]], faces: tuple[str, str], size: float, width: float, bold_all: bool = False) -> list[list[tuple[str, bool]]]:
    """Logical lines (lists of (word, bold)) that each fit `width` points."""
    space = stringWidth(" ", faces[0], size)
    lines, line, used = [], [], 0.0
    for word, bold in _tokens(runs, bold_all):
        w = _shaped_width(word, faces[1] if bold else faces[0], size)
        if line and used + space + w > width:
            lines.append(line)
            line, used = [], 0.0
        used += (space if line else 0) + w
        line.append((word, bold))
    return lines + ([line] if line else [])


def _line_markup(line: list[tuple[str, bool]]) -> str:
    shown = visual(" ".join(w for w, _ in line))
    flags, taken = [False] * len(shown), [False] * len(shown)
    for word, bold in line:
        if not bold:
            continue
        piece = visual(word)
        at = next((i for i in range(len(shown) - len(piece) + 1) if shown[i:i + len(piece)] == piece and not any(taken[i:i + len(piece)])), -1)
        if at >= 0:
            flags[at:at + len(piece)] = [True] * len(piece)
            taken[at:at + len(piece)] = [True] * len(piece)
    out, i = [], 0
    while i < len(shown):
        j = i
        while j < len(shown) and flags[j] == flags[i]:
            j += 1
        chunk = escape(shown[i:j])
        out.append(f"<b>{chunk}</b>" if flags[i] else chunk)
        i = j
    return "".join(out)


def rtl_markup(runs: list[tuple[str, bool]], faces: tuple[str, str], size: float, width: float, bold_all: bool = False) -> str:
    return "<br/>".join(_line_markup(line) for line in wrap_lines(runs, faces, size, width, bold_all))
