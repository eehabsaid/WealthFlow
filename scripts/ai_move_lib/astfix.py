"""AST-level pre-move fixes (run on the OLD tree, before the text rewrite).

1. Relative imports that cross a move boundary become absolute (old names).
2. Names re-exported by aggregators (core.models, core.views, ...) that
   originate in moved modules are imported from their real module instead.
3. Aggregator files drop their imports of moved modules.
"""
import ast
import os
import re

from . import imports

AGGREGATORS = ["core.models", "core.views", "core.views.settings", "core.urls"]


def _map(name, mmap):
    for k in sorted(mmap, key=len, reverse=True):
        if name == k or name.startswith(k + "."):
            return mmap[k] + name[len(k):]
    return name


def _is_moved(mod, mmap):
    return any(mod == k or mod.startswith(k + ".") for k in mmap)


def _fmt(base, names):
    items = ", ".join(n.name + (f" as {n.asname}" if n.asname else "") for n in names)
    one = f"from {base} import {items}"
    if len(one) <= 150:
        return one
    body = "".join(f"    {n.name}{' as ' + n.asname if n.asname else ''},\n" for n in names)
    return f"from {base} import (\n{body})"


def aggregator_origins(root, mods, mmap):
    """{aggregator: {name: origin_module}} for names whose origin moved."""
    out = {}
    for agg in AGGREGATORS:
        rel = mods.get(agg)
        if not rel:
            continue
        with open(os.path.join(root, rel), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        is_pkg = rel.endswith("__init__.py")
        d = {}
        for n in tree.body:
            if isinstance(n, ast.ImportFrom):
                base = imports._abs(agg, is_pkg, n.level, n.module or "")
                if _is_moved(base, mmap):
                    for a in n.names:
                        d[a.asname or a.name] = base
        out[agg] = d
    return out


def fix_file(root, rel, mods, mmap, origins):
    path = os.path.join(root, rel)
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False
    mod = next((m for m, r in mods.items() if r == rel), None)
    if mod is None:
        return False
    is_pkg = rel.endswith("__init__.py")
    moved_self = _is_moved(mod, mmap)
    lines, edits = src.split("\n"), []
    for n in ast.walk(tree):
        if not isinstance(n, ast.ImportFrom):
            continue
        base = imports._abs(mod, is_pkg, n.level, n.module or "")
        conv = [a for a in n.names if a.name != "*" and f"{base}.{a.name}" in mmap
                and mmap[f"{base}.{a.name}"].rsplit(".", 1)[0] != _map(base, mmap)]
        if conv:
            keep = [a for a in n.names if a not in conv]
            parts = ([_fmt(base, keep)] if keep else []) + [
                f"import {base}.{a.name} as {a.asname or a.name}" for a in conv]
            edits.append((n.lineno, n.end_lineno, "\n".join(parts)))
        elif mod in origins and not moved_self and _is_moved(base, mmap):
            edits.append((n.lineno, n.end_lineno, ""))
        elif n.level and (moved_self or _is_moved(base, mmap)) and \
                imports._abs(_map(mod, mmap), is_pkg, n.level, n.module or "") != _map(base, mmap):
            edits.append((n.lineno, n.end_lineno, _fmt(base, n.names)))
        elif base in origins and mod != base:
            moved = [a for a in n.names if a.name in origins[base]]
            if moved:
                keep = [a for a in n.names if a.name not in origins[base]]
                by = {}
                for a in moved:
                    by.setdefault(origins[base][a.name], []).append(a)
                parts = [_fmt(k, v) for k, v in sorted(by.items())]
                if keep:
                    parts.insert(0, _fmt(base, keep))
                edits.append((n.lineno, n.end_lineno, "\n".join(parts)))
    ind = {n.lineno: " " * n.col_offset for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    for s_, e_, rep in sorted(set(edits), reverse=True):
        pad = ind.get(s_, "")
        lines[s_ - 1:e_] = [pad + r for r in rep.split("\n")] if rep else []
    text = "\n".join(lines)
    if mod in origins and not moved_self:
        for name in origins[mod]:
            text = re.sub(r"^[ \t]*[\"']%s[\"'],?[ \t]*\n" % re.escape(name), "", text, flags=re.M)
    if text == src:
        return False
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return True
