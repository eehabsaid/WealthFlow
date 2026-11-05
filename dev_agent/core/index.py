"""Repo index built from the source itself (AST for Python, a light scan for JS): files, classes, functions, models, imports, routes,
and who imports what. Rebuilt automatically when any indexed file changed. Adapted from core/services/ai/coding/index.py, no Django."""

from __future__ import annotations

import ast
import os
import re

from .project import ALWAYS_EXCLUDE

CODE_EXT = (".py", ".js", ".ts", ".css", ".html")
MAX_BYTES = 1_000_000
_JS_DEF = re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)|^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\(|function|\w+\s*=>)", re.M)
_JS_IMPORT = re.compile(r"""(?:from\s+|import\s+|require\(\s*)['"]([^'"]+)['"]""")
WORD = re.compile(r"[a-z0-9_]{3,}")


def _py(text: str) -> dict:
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
    return {"lines": text.count("\n") + 1, "classes": [], "functions": names, "models": {}, "imports": _JS_IMPORT.findall(text), "routes": []}


def _words(text: str) -> set[str]:
    return set(WORD.findall(text.lower()))


class Index:
    def __init__(self, project):
        self.project = project
        self._stamp = None
        self._files: dict = {}

    def _walk(self):
        skip = ALWAYS_EXCLUDE | set(self.project.config["index_exclude"])
        for root_rel in self.project.config.get("agent_index_roots") or self.project.config["index_roots"]:
            base = self.project.root / root_rel
            for folder, dirs, names in os.walk(base):
                dirs[:] = [d for d in dirs if d not in skip]
                for name in names:
                    if name.endswith(CODE_EXT):
                        yield os.path.join(folder, name)

    def get(self) -> dict:
        paths = list(self._walk())
        stamp = (len(paths), max((os.stat(p).st_mtime_ns for p in paths), default=0))
        if stamp != self._stamp:
            files = {}
            for full in paths:
                try:
                    if os.path.getsize(full) > MAX_BYTES:
                        continue
                    text = open(full, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                rel = os.path.relpath(full, self.project.root).replace("\\", "/")
                files[rel] = _py(text) if rel.endswith(".py") else _js(text) if rel.endswith((".js", ".ts")) else {
                    "lines": text.count("\n") + 1, "classes": [], "functions": [], "models": {}, "imports": [], "routes": []}
            self._files, self._stamp = files, stamp
        return self._files

    def callers(self, name: str) -> list[str]:
        """Files that import `name` (a module, class or function name)."""
        return sorted(p for p, e in self.get().items() if any(name in re.split(r"[./\\]", i) for i in e["imports"]))

    def search(self, query: str, limit: int = 15) -> list[dict]:
        words = _words(query)
        rows = []
        for path, e in self.get().items():
            symbols = e["classes"] + e["functions"] + list(e["models"])
            score = 3 * len(words & _words(path.replace("/", " "))) + 2 * len(words & _words(" ".join(symbols))) + len(words & _words(" ".join(e["imports"])))
            if score:
                rows.append({"path": path, "lines": e["lines"], "classes": e["classes"][:5], "functions": e["functions"][:8], "score": score})
        return sorted(rows, key=lambda r: (-r["score"], r["path"]))[:limit]
