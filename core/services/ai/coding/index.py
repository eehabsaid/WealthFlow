"""Repo index built from the source itself (AST for Python, a light scan for JavaScript): files, classes, functions, models and
their fields, URL routes, dependencies, and who imports what. Rebuilt automatically when any file changed."""

from __future__ import annotations

import ast
import json
import re

from . import ROOT
from .config import load

_JS_DEF = re.compile(r"^(?:async\s+)?function\s+(\w+)|^(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\(|function|\w+\s*=>)", re.M)
_cache: dict = {"stamp": None, "index": None}


def _py(path, text: str) -> dict:
    entry = {"lines": text.count("\n") + 1, "classes": [], "functions": [], "models": {}, "imports": [], "routes": []}
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return entry
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            entry["imports"] += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            entry["imports"] += [f"{node.module}.{a.name}" for a in node.names]
        elif isinstance(node, ast.Call) and getattr(node.func, "id", "") in ("path", "re_path") and node.args and isinstance(node.args[0], ast.Constant):
            entry["routes"].append(str(node.args[0].value))
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            entry["classes"].append(node.name)
            fields = [t.id for s in node.body if isinstance(s, ast.Assign) and isinstance(s.value, ast.Call) and "models." in ast.unparse(s.value.func)
                      for t in s.targets if isinstance(t, ast.Name)]
            if fields:
                entry["models"][node.name] = fields
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            entry["functions"].append(node.name)
    return entry


def _js(text: str) -> dict:
    names = [a or b for a, b in _JS_DEF.findall(text)]
    return {"lines": text.count("\n") + 1, "classes": [], "functions": names, "models": {}, "imports": [], "routes": []}


def _files():
    for root in load()["index_roots"]:
        base = ROOT / root
        for f in sorted(base.rglob("*")) if base.is_dir() else []:
            if f.suffix in (".py", ".js") and "__pycache__" not in f.parts and "node_modules" not in f.parts and "migrations" not in f.parts:
                yield f


def _deps() -> dict:
    out = {"python": [], "node": []}
    req = ROOT / "requirements.txt"
    if req.exists():
        raw = req.read_bytes()
        text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", "replace")
        out["python"] = sorted({line.split("==")[0].strip() for line in text.splitlines() if line.strip() and not line.startswith("#")})
    pkg = ROOT / "package.json"
    if pkg.exists():
        data = json.loads(pkg.read_text(encoding="utf-8") or "{}")
        out["node"] = sorted({**data.get("dependencies", {}), **data.get("devDependencies", {})})
    return out


def build() -> dict:
    files = {}
    for f in _files():
        text = f.read_text(encoding="utf-8", errors="replace")
        files[f.relative_to(ROOT).as_posix()] = _py(f, text) if f.suffix == ".py" else _js(text)
    return {"files": files, "dependencies": _deps()}


def get() -> dict:
    stamp = tuple((f.as_posix(), f.stat().st_mtime_ns) for f in _files())
    if _cache["stamp"] != stamp:
        _cache.update(stamp=stamp, index=build())
    return _cache["index"]


def find(query: str, limit: int = 25) -> list[dict]:
    """Files, classes, functions, models, routes whose name contains `query` (case-insensitive)."""
    q = query.strip().lower()
    hits = []
    for path, e in get()["files"].items():
        found = [n for n in e["classes"] + e["functions"] + list(e["models"]) + e["routes"] if q in n.lower()]
        if q in path.lower() or found:
            hits.append({"file": path, "lines": e["lines"], "matches": found[:8], "models": {m: f for m, f in e["models"].items() if q in m.lower()}})
    return hits[:limit]


def callers(symbol: str, limit: int = 40) -> list[str]:
    """Files that import `symbol` (a class / function name) or a module path containing it."""
    s = symbol.strip()
    return [p for p, e in get()["files"].items() if any(i.split(".")[-1] == s or i.endswith("." + s) or i == s or s in i.split(".") for i in e["imports"])][:limit]
