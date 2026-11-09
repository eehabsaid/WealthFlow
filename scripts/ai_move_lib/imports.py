"""Static import analysis: unresolved imports, module-level import graph, cycles."""
import ast
import os

from . import inventory


def _modules(root):
    mods = {}
    for rel in inventory.walk(root):
        m = inventory.to_module(rel)
        if m:
            mods[m] = rel
    return mods


def _top_names(tree):
    names, star = set(), False
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            names.add(n.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                if a.name == "*":
                    star = True
                names.add((a.asname or a.name).split(".")[0])
    return names, star


def _abs(mod, is_pkg, level, name):
    if not level:
        return name
    parts = mod.split(".")
    base = parts if is_pkg else parts[:-1]
    base = base[: len(base) - (level - 1)] if level > 1 else base
    return ".".join(base + ([name] if name else []))


def analyse(root):
    """Return (unresolved set, module-level edges dict)."""
    mods = _modules(root)
    for m, rel in list(mods.items()):  # namespace packages (folders without __init__.py)
        parts = m.split(".")
        for i in range(1, len(parts)):
            mods.setdefault(".".join(parts[:i]), None)
    tops = {m.split(".")[0] for m in mods}
    cache, unresolved, edges = {}, set(), {}

    def names_of(m):
        if m not in cache:
            try:
                if mods[m] is None:
                    cache[m] = (set(), True)
                    return cache[m]
                with open(os.path.join(root, mods[m]), encoding="utf-8") as fh:
                    text = fh.read()
                names, star = _top_names(ast.parse(text))
                cache[m] = (names, star or "globals()" in text or "__getattr__" in text)
            except (SyntaxError, UnicodeDecodeError, OSError):
                cache[m] = (set(), True)
        return cache[m]

    for mod, rel in mods.items():
        if rel is None:
            continue
        is_pkg = rel.endswith("__init__.py")
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
        except (SyntaxError, UnicodeDecodeError):
            continue
        toplevel = set()
        for stmt in tree.body:
            for n in ast.walk(stmt) if isinstance(stmt, (ast.If, ast.Try)) else [stmt]:
                if isinstance(n, (ast.Import, ast.ImportFrom)):
                    toplevel.add(id(n))
        edges.setdefault(mod, set())
        for n in ast.walk(tree):
            targets = []
            if isinstance(n, ast.Import):
                targets = [(a.name, None) for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                base = _abs(mod, is_pkg, n.level, n.module or "")
                targets = [(base, a.name) for a in n.names]
            for base, name in targets:
                if base.split(".")[0] not in tops:
                    continue
                if base not in mods:
                    unresolved.add((rel, base, name or ""))
                    continue
                dest = base
                if name and name != "*":
                    sub = f"{base}.{name}"
                    if sub in mods:
                        dest = sub
                    else:
                        ns, star = names_of(base)
                        if name not in ns and not star:
                            unresolved.add((rel, base, name))
                if id(n) in toplevel or n in tree.body:
                    edges[mod].add(dest)
    return unresolved, edges


def cycles(edges):
    """Strongly connected components of size > 1 (iterative Tarjan)."""
    index, low, on, stack, out, counter = {}, {}, set(), [], [], [0]
    for v0 in edges:
        if v0 in index:
            continue
        work = [(v0, iter(sorted(edges.get(v0, ()))))]
        index[v0] = low[v0] = counter[0]; counter[0] += 1
        stack.append(v0); on.add(v0)
        while work:
            v, it = work[-1]
            for w in it:
                if w not in edges:
                    continue
                if w not in index:
                    index[w] = low[w] = counter[0]; counter[0] += 1
                    stack.append(w); on.add(w)
                    work.append((w, iter(sorted(edges.get(w, ())))))
                    break
                if w in on:
                    low[v] = min(low[v], index[w])
            else:
                work.pop()
                if work:
                    low[work[-1][0]] = min(low[work[-1][0]], low[v])
                if low[v] == index[v]:
                    comp = []
                    while True:
                        w = stack.pop(); on.discard(w); comp.append(w)
                        if w == v:
                            break
                    if len(comp) > 1:
                        out.append(sorted(comp))
    return out
