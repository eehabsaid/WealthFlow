"""Python structural parser (stdlib `ast`): classes, functions, methods, constants, imports, calls; then the Django layer."""

from __future__ import annotations

import ast

from ai.services.knowledge_index.parsers import make_symbol
from ai.services.knowledge_index.parsers import py_django

_FUNC = (ast.FunctionDef, ast.AsyncFunctionDef)


def _sig(node) -> str:
    if isinstance(node, ast.ClassDef):
        return f"class {node.name}({', '.join(ast.unparse(b) for b in node.bases)})"
    args = ast.unparse(node.args)
    return f"{'async ' if isinstance(node, ast.AsyncFunctionDef) else ''}def {node.name}({args})"


def _body(lines: list[str], node) -> str:
    return "\n".join(lines[node.lineno - 1: min(node.end_lineno or node.lineno, node.lineno + 40)])


def _callee(func) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _collect_calls(node, src: str, refs: list[dict]) -> None:
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            name = _callee(child.func)
            if name:
                refs.append({"line": child.lineno, "src": src, "name": name, "kind": "call"})


def _walk(body, lines, symbols, refs, parent="") -> None:
    for node in body:
        if isinstance(node, (ast.ClassDef, *_FUNC)):
            kind = "class" if isinstance(node, ast.ClassDef) else ("method" if parent else "function")
            sym = make_symbol(node.name, kind, node.lineno, node.end_lineno or node.lineno, parent=parent, sig=_sig(node),
                              doc=ast.get_docstring(node) or "", body=_body(lines, node))
            symbols.append(sym)
            for dec in node.decorator_list:
                refs.append({"line": dec.lineno, "src": sym["qname"], "name": _callee(dec.func if isinstance(dec, ast.Call) else dec)
                             or "decorator", "kind": "call"})
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    refs.append({"line": node.lineno, "src": sym["qname"], "name": ast.unparse(base).split(".")[-1], "kind": "import"})
                _walk(node.body, lines, symbols, refs, sym["qname"])
            else:
                _collect_calls(ast.Module(body=node.body, type_ignores=[]), sym["qname"], refs)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = getattr(node, "module", None) or ""
            for alias in node.names:
                refs.append({"line": node.lineno, "src": parent, "name": alias.name.split(".")[-1], "kind": "import"})
                if mod:
                    refs.append({"line": node.lineno, "src": parent, "name": f"{mod}.{alias.name}", "kind": "import"})
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and not parent:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    symbols.append(make_symbol(t.id, "variable", node.lineno, node.end_lineno or node.lineno,
                                               sig=ast.unparse(node)[:120], body=_body(lines, node)))
            _collect_calls(node, "", refs)
        elif not parent and not isinstance(node, (ast.Expr,)) or isinstance(node, ast.Expr):
            _collect_calls(node, parent, refs)
            if isinstance(node, (ast.If, ast.Try, ast.With, ast.For)):
                _walk(getattr(node, "body", []), lines, symbols, refs, parent)


def parse(rel: str, text: str) -> tuple[list[dict], list[dict]]:
    symbols: list[dict] = []
    refs: list[dict] = []
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [make_symbol("<syntax-error>", "error", exc.lineno or 1, exc.lineno or 1, doc=str(exc.msg))], refs
    lines = text.splitlines()
    doc = ast.get_docstring(tree)
    if doc:
        symbols.append(make_symbol(rel.rsplit("/", 1)[-1], "module", 1, min(len(lines), 5), doc=doc))
    _walk(tree.body, lines, symbols, refs)
    py_django.extend(rel, tree, lines, symbols, refs)
    return symbols, refs
