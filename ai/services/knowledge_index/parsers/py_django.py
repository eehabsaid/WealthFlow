"""Django layer on top of the Python AST: models + fields + relations, URL patterns -> views, migration operations."""

from __future__ import annotations

import ast

from ai.services.knowledge_index.parsers import make_symbol

_REL = ("ForeignKey", "OneToOneField", "ManyToManyField")


def _is_model(node: ast.ClassDef) -> bool:
    return any(ast.unparse(b).split(".")[-1] in ("Model", "AbstractUser", "TimeStampedModel") or ast.unparse(b).endswith("Mixin")
               for b in node.bases)


def _target(call: ast.Call, class_name: str) -> str:
    if not call.args:
        return ""
    arg = call.args[0]
    text = str(arg.value) if isinstance(arg, ast.Constant) else ast.unparse(arg)
    if text in ("self", "'self'"):
        return class_name
    return "User" if text.endswith("AUTH_USER_MODEL") else text.split(".")[-1]


def _models(tree, symbols, refs) -> None:
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and _is_model(n)):
        for stmt in cls.body:
            if not (isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call)):
                continue
            kind = ast.unparse(stmt.value.func).split(".")[-1]
            if not kind.endswith(("Field", "Key")) and kind not in _REL:
                continue
            for t in (x for x in stmt.targets if isinstance(x, ast.Name)):
                symbols.append(make_symbol(t.id, "field", stmt.lineno, stmt.end_lineno or stmt.lineno, parent=cls.name,
                                           sig=ast.unparse(stmt)[:200], body=ast.unparse(stmt)))
                if kind in _REL and _target(stmt.value, cls.name):
                    refs.append({"line": stmt.lineno, "src": f"{cls.name}.{t.id}", "name": _target(stmt.value, cls.name), "kind": "fk"})


def _view_name(arg) -> str:
    if isinstance(arg, ast.Call):
        if isinstance(arg.func, ast.Attribute) and arg.func.attr == "as_view":
            return _view_name(arg.func.value)
        return _view_name(arg.args[0]) if arg.args else _view_name(arg.func)   # wrapper(View.as_view()) -> View
    return arg.attr if isinstance(arg, ast.Attribute) else (arg.id if isinstance(arg, ast.Name) else "")


def _urls(tree, symbols, refs) -> None:
    for call in (n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))):
        fname = call.func.id if isinstance(call.func, ast.Name) else call.func.attr
        if fname not in ("path", "re_path", "include") or not call.args:
            continue
        first = call.args[0]
        if fname == "include":
            mod = str(first.value) if isinstance(first, ast.Constant) else ast.unparse(first)
            refs.append({"line": call.lineno, "src": "", "name": mod, "kind": "include"})
            continue
        if not isinstance(first, ast.Constant) or len(call.args) < 2:
            continue
        pattern = str(first.value)
        symbols.append(make_symbol(pattern or "/", "route", call.lineno, call.end_lineno or call.lineno, sig=ast.unparse(call)[:200]))
        view = _view_name(call.args[1])
        if view:
            refs.append({"line": call.lineno, "src": pattern or "/", "name": view, "kind": "route_view"})
        for kw in call.keywords:
            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                refs.append({"line": call.lineno, "src": pattern or "/", "name": str(kw.value.value), "kind": "url_name"})


def _migrations(tree, symbols) -> None:
    for call in (n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
        op = call.func.attr
        if op not in ("CreateModel", "AddField", "AlterField", "RemoveField", "DeleteModel", "RenameField", "RenameModel", "AddIndex"):
            continue
        kw = {k.arg: k.value.value for k in call.keywords if isinstance(k.value, ast.Constant)}
        model = str(kw.get("model_name") or kw.get("name") or kw.get("old_name") or "")
        field = str(kw.get("name") if op != "CreateModel" else "") if kw.get("name") else ""
        label = f"{op}:{model}{'.' + field if field and field != model else ''}"
        symbols.append(make_symbol(label, "migration_op", call.lineno, call.end_lineno or call.lineno))


def extend(rel: str, tree, lines, symbols, refs) -> None:
    if "/migrations/" in rel:
        _migrations(tree, symbols)
        return
    _models(tree, symbols, refs)
    if rel.endswith("urls.py") or "/urls/" in rel or "urls_" in rel.rsplit("/", 1)[-1]:
        _urls(tree, symbols, refs)
