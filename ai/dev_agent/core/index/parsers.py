"""File parsers for the repo index: Python (AST), JS (light scan), HTML."""

from __future__ import annotations

import ast
import hashlib
import re



CODE_EXT = (".py", ".js", ".ts", ".css", ".html")
MAX_BYTES = 1_000_000
_JS_DEF = re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)|^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\(|function|\w+\s*=>)", re.M)
_JS_IMPORT = re.compile(r"""(?:from\s+|import\s+|require\(\s*)['\"]([^'\"]+)['\"]""")
WORD = re.compile(r"[a-z0-9_]{3,}")
INDEX_VERSION = 1


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


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


def _html(text: str) -> dict:
    return {"lines": text.count("\n") + 1, "classes": [], "functions": [], "models": {}, "imports": [], "routes": []}


def _words(text: str) -> set[str]:
    return set(WORD.findall(text.lower()))
