"""API endpoint string literals in JS / inline scripts ('/api/expenses/', `/api/x/${id}/`): links frontend code to Django routes."""

from __future__ import annotations

import re

_LITERAL = re.compile(r"""(['"`])(/?api/[^'"`\s]*)\1""")


def normalise(url: str) -> str:
    """'/api/x/${id}/?a=1' -> 'api/x/{}/'  (leading slash and query string dropped, template holes become {})."""
    url = re.sub(r"\$\{[^}]*\}", "{}", url.split("?")[0]).lstrip("/")
    return url


def add(text: str, symbols: list[dict], refs: list[dict], line_offset: int = 0) -> None:
    scoped = sorted((s for s in symbols if s["kind"] in ("function", "method", "class")), key=lambda s: s["end"] - s["line"])
    for no, line in enumerate(text.splitlines(), 1):
        for m in _LITERAL.finditer(line):
            n = no + line_offset
            src = next((s["qname"] for s in scoped if s["line"] <= n <= s["end"]), "")
            refs.append({"line": n, "src": src, "name": normalise(m.group(2)), "kind": "endpoint"})
