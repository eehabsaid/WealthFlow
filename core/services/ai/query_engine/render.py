"""Generic renderer: QueryResult -> markdown. Single values, tables, bold per-group / grand-total rows.
Pure string work (labels already localised by the executor); the LLM never writes a table or adds numbers."""

from __future__ import annotations

from .spec import QueryResult


def render(result: QueryResult) -> str:
    if not result.columns:
        text = result.intro
    else:
        n = len(result.columns)
        lines = [result.intro, "", "| " + " | ".join(result.columns) + " |", "|" + "---|" * n]
        for row in result.rows:
            cells = [f"**{c}**" if row.bold and c else c for c in row.cells]
            lines.append("| " + " | ".join(cells) + " |")
        text = "\n".join(lines)
    return f"{text}\n\n{result.footer}" if result.footer else text
