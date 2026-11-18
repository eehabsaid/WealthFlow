"""Pure-Python structural scanner for script-global JavaScript (the fallback when Acorn/Node is unavailable).

It first blanks strings, comments and template literals (keeping line numbers), then tracks brace depth to find declarations:
top-level function/class/var/let/const (these are script-globals), `window.name = ...`, namespace members (`Obj.fn = function`),
class methods, and the references each one makes. Identifier references are kept as kind `ident`; resolution against the
set of globals defined in ANY file happens at query time, which is what preserves cross-file global references.
"""

from __future__ import annotations

import re

from ai.services.knowledge_index.parsers import make_symbol

KEYWORDS = frozenset("""break case catch class const continue debugger default delete do else export extends finally for function if import in
instanceof let new return super switch this throw try typeof var void while with yield await async of static get set null true false
undefined NaN Infinity console window document globalThis self""".split())
_DECL = re.compile(r"""(?:^|[;{}\n])\s*(?:(?P<fn>(?:async\s+)?function\s*\*?\s*(?P<fname>[\w$]+))|(?P<cls>class\s+(?P<cname>[\w$]+))|(?P<var>(?:var|let|const)\s+(?P<vname>[\w$]+)\s*=\s*(?P<vinit>async\s+function|function|class|async\s*\(|async\s+[\w$]+\s*=>|\([^)]*\)\s*=>|[\w$]+\s*=>)?)|(?P<win>(?:window|globalThis)\.(?P<wname>[\w$]+)\s*=\s*(?P<winit>async\s+function|function|\([^)]*\)\s*=>)?)|(?P<ns>(?P<nsobj>[A-Za-z_$][\w$]*)\.(?P<nsname>[\w$]+)\s*=\s*(?P<nsinit>async\s+function|function|\([^)]*\)\s*=>)))""")
_METHOD = re.compile(r"^\s*(?:static\s+|async\s+|get\s+|set\s+)*(?P<m>[\w$]+)\s*\([^)]*\)\s*\{")
_IDENT = re.compile(r"(?<![\w$.])([A-Za-z_$][\w$]*)")
_CALL = re.compile(r"(?<![\w$])([A-Za-z_$][\w$]*)\s*\(")
_MEMBER_CALL = re.compile(r"\.([A-Za-z_$][\w$]*)\s*\(")
_WINDOW = re.compile(r"(?:window|globalThis)\.([A-Za-z_$][\w$]*)")


def blank(text: str) -> str:
    """Replace comments and string/template/regex-free contents with spaces, preserving newlines and length."""
    out, i, n = [], 0, len(text)
    while i < n:
        c, nxt = text[i], text[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i)); i = j
        elif c == "/" and nxt == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", text[i:j])); i = j
        elif c in "'\"`":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
                if c != "`" and j < n and text[j] == "\n":
                    break
            j = min(n, j + 1)
            out.append(c + re.sub(r"[^\n]", " ", text[i + 1: j - 1]) + (c if j - 1 > i else "")); i = j
        else:
            out.append(c); i += 1
    return "".join(out)


def _end_line(clean: str, start: int, start_line: int) -> int:
    """Line where the first `{` at/after `start` closes (or the statement ends)."""
    depth, i, n, seen = 0, start, len(clean), False
    while i < n:
        c = clean[i]
        if c == "{":
            depth += 1; seen = True
        elif c == "}":
            depth -= 1
            if seen and depth == 0:
                return clean.count("\n", 0, i) + 1
        elif c == ";" and not seen:
            return clean.count("\n", 0, i) + 1
        i += 1
    return start_line


def _decl_kind(m, depth: int):
    if m.group("fname"):
        return m.group("fname"), "function", "global" if depth == 0 else "local"
    if m.group("cname"):
        return m.group("cname"), "class", "global" if depth == 0 else "local"
    if m.group("vname"):
        fn = bool(m.group("vinit"))
        return m.group("vname"), "function" if fn else "variable", "global" if depth == 0 else "local"
    if m.group("wname"):
        return m.group("wname"), "function" if m.group("winit") else "variable", "global"
    return m.group("nsname"), "function", "member:" + m.group("nsobj")


def _decls(clean: str, lines: list[str]) -> list[dict]:
    depth_at = []
    depth = 0
    for ch in clean:
        depth_at.append(depth)
        depth += (ch == "{") - (ch == "}")
    out = []
    for m in _DECL.finditer(clean):
        start = m.start() + len(m.group(0)) - len(m.group(0).lstrip("\n;{} \t"))
        depth = depth_at[min(start, len(depth_at) - 1)]
        name, kind, scope = _decl_kind(m, depth)
        if depth > 0 and scope == "local":
            continue
        line = clean.count("\n", 0, start) + 1
        end = _end_line(clean, m.end() - 1 if kind != "variable" else start, line) if kind != "variable" else line
        parent = scope[7:] if scope.startswith("member:") else ""
        if parent in ("this", "module", "exports", "prototype") or name in KEYWORDS:
            continue
        sym = make_symbol(name, kind, line, end, parent=parent, sig=lines[line - 1].strip()[:200], body="\n".join(lines[line - 1: min(end, line + 30)]))
        sym["scope"] = scope
        out.append(sym)
    return out


def _methods(clean: str, lines: list[str], classes: list[dict]) -> list[dict]:
    out = []
    for cls in classes:
        if cls["kind"] != "class":
            continue
        for ln in range(cls["line"] + 1, cls["end"]):
            m = _METHOD.match(clean.split("\n")[ln - 1])
            if m and m.group("m") not in KEYWORDS:
                end = _end_line(clean, sum(len(x) + 1 for x in clean.split("\n")[: ln - 1]), ln)
                out.append(make_symbol(m.group("m"), "method", ln, end, parent=cls["name"], sig=lines[ln - 1].strip()[:200],
                                       body="\n".join(lines[ln - 1: min(end, ln + 30)])))
    return out


def parse(text: str) -> tuple[list[dict], list[dict]]:
    lines = text.splitlines()
    clean = blank(text)
    symbols = _decls(clean, lines)
    symbols += _methods(clean, lines, symbols)
    scoped = sorted((s for s in symbols if s["kind"] in ("function", "method", "class")), key=lambda s: s["end"] - s["line"])
    refs = []
    for no, line in enumerate(clean.split("\n"), 1):
        if not line.strip():
            continue
        src = next((s["qname"] for s in scoped if s["line"] <= no <= s["end"]), "")
        for rx, kind in ((_CALL, "call"), (_MEMBER_CALL, "call"), (_WINDOW, "ident"), (_IDENT, "ident")):
            for m in rx.finditer(line):
                if m.group(1) not in KEYWORDS:
                    refs.append({"line": no, "src": src, "name": m.group(1), "kind": kind})
    seen, unique = set(), []
    for r in refs:
        key = (r["line"], r["name"], r["kind"] if r["kind"] == "call" else "ident")
        if key not in seen:
            seen.add(key); unique.append(r)
    return symbols, unique
