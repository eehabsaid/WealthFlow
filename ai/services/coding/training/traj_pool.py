"""Facts about the source files a training task list can be drawn from, read with `ast` and git - never guessed.

tracked()     the files git tracks (a folder walk when there is no git).
used_files()  every tracked file an earlier task already touched or talked about: the review files, and for each task folder under coding_agent/tasks its goal,
              answer, plan, written files and report. A new task list uses none of them (`ignore` leaves out folders the batch itself made).
candidates()  the product source files a task can be about: Python modules, and the plain scripts under static/js (no tests, migrations, vendor or minified
              code, the dev agent itself, scripts, templates).
read()        what is really in one file: module docstring, functions (public, parameters without a type hint, docstring, body length), classes, bare `except:`,
              project imports (JavaScript: its top-level functions), and `mapped` = a change to the file can reach VERIFIED (its folder maps to a Django test
              module or a pytest area in config.json; otherwise the agent's own result is always "NOT VERIFIED").
usage()       which tracked files (tests left out) mention each name."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
from pathlib import Path

SKIP = re.compile(r"(^|/)(node_modules|migrations|vendor|tests?|test_[^/]*|conftest\.py|dev_agent|__pycache__)(/|$)")
SKIP_TOP = ("scripts/", ".agents/", "wealthflow/", "static/", "templates/", "manage.py")
TESTS = re.compile(r"(^|/)(tests?|test_[^/]*)(/|$)")
# Money, salary, billing and login code: a PATCH task never touches it (a question about it is fine - reading changes nothing).
SENSITIVE = re.compile(r"balance|salary|payroll|per_diem|cash_?flow|billing|subscription|payment|invoice|password|permission|ownership|credential|secret|token|"
                       r"certificate|expense|income|transfer|deposit|withdraw|currency|exchange_rate|receipt|budget|recurring|auto_post|posting|"
                       r"(?<![a-z])(?:trial|auth|bank|rent|sale|sell)", re.I)
MENTION = re.compile(r"[\w./-]+\.(?:py|js|css|html|json|md)")
BARE_EXCEPT = re.compile(r"^\s*except\s*:\s*(#.*)?$", re.M)
PROJECT_PACKAGES = ("ai", "core")   # ai-independence: ok - data about the repo being read: an import of these counts as "a module of this project" (never imported here)
JS_FUNCTION = re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_]\w*)\s*\(([^)]*)\)", re.M)


def tracked(root) -> list[str]:
    root = Path(root)
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout.decode("utf-8", "replace")
        return sorted(p for p in out.split("\0") if p)
    except (OSError, subprocess.CalledProcessError):
        found = []
        for folder, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__")]
            found += [os.path.relpath(os.path.join(folder, n), root).replace("\\", "/") for n in names]
        return sorted(found)


def _read(root, rel: str) -> str:
    try:
        return (Path(root) / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def used_files(project, files: list[str], ignore=()) -> set[str]:
    """Tracked files named by an earlier task (a mention may leave out the leading folder: 'dev_agent/guard/commands.py' is 'ai/dev_agent/guard/commands.py')."""
    texts = []
    for name in ("qa_review.jsonl", "patch_review.jsonl"):
        for line in _read(project.root, f"coding_agent/{name}").splitlines():
            try:
                example = json.loads(line)["example"]
            except (ValueError, KeyError, TypeError):
                continue
            texts += [example.get("goal", ""), example.get("answer", ""), *example.get("files", [])]
    tasks = Path(project.root) / "coding_agent" / "tasks"
    for folder in sorted(tasks.iterdir()) if tasks.is_dir() else []:
        if folder.name in ignore:
            continue
        try:
            data = json.loads((folder / "ledger.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        texts += [str(data.get("goal", "")), str(data.get("answer", "")), json.dumps(data.get("plan") or {}), *(data.get("files") or {}), _read(folder, "report.md")]
    mentioned = {m for text in texts for m in MENTION.findall(text) if "/" in m}
    return {f for f in files for m in mentioned if f == m or f.endswith("/" + m)}


def candidates(project, files: list[str], used: set[str], low: int = 25, high: int = 185) -> list[str]:
    out = []
    for rel in files:
        python = rel.endswith(".py") and not rel.startswith(SKIP_TOP)
        script = rel.startswith("static/js/") and rel.endswith(".js") and ".min." not in rel
        if not (python or script) or rel in used or SKIP.search(rel) or project.protected_reason(rel):
            continue
        if low <= len(_read(project.root, rel).splitlines()) <= high:
            out.append(rel)
    return out


def _js_facts(source: str, rel: str) -> dict:
    lines, functions = source.splitlines(), []
    for match in JS_FUNCTION.finditer(source):
        start = source[:match.start()].count("\n")
        end = next((i for i in range(start + 1, len(lines)) if lines[i] == "}"), None)   # a top-level function ends at the first brace in column 0
        if end is not None:
            functions.append({"name": match.group(1), "line": start + 1, "args": [a.strip() for a in match.group(2).split(",") if a.strip()], "doc": False,
                              "body_lines": end - start, "public": True, "missing_hints": []})
    return {"path": rel, "lines": len(lines), "module_doc": False, "functions": functions, "classes": [], "imports": [], "bare_except": []}


def _function(node) -> dict:
    args = [a.arg for a in node.args.args + node.args.kwonlyargs if a.arg not in ("self", "cls")]
    unhinted = [a.arg for a in node.args.args + node.args.kwonlyargs if a.annotation is None and a.arg not in ("self", "cls")]
    return {"name": node.name, "line": node.lineno, "args": args, "missing_hints": unhinted + (["return"] if node.returns is None else []),
            "doc": ast.get_docstring(node) is not None, "body_lines": node.end_lineno - node.lineno, "public": not node.name.startswith("_")}


def facts(root, rel: str) -> dict | None:
    """What is really in `rel`, or None when it does not parse."""
    source = _read(root, rel)
    if rel.endswith(".js"):
        return _js_facts(source, rel)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    functions = [_function(n) for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    classes = [{"name": n.name, "line": n.lineno, "doc": ast.get_docstring(n) is not None, "methods": sum(isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) for m in n.body)}
               for n in tree.body if isinstance(n, ast.ClassDef)]
    imports = sorted({n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module and n.module.split(".")[0] in PROJECT_PACKAGES and n.level == 0})
    return {"path": rel, "lines": len(source.splitlines()), "module_doc": ast.get_docstring(tree) is not None, "functions": functions, "classes": classes,
            "imports": imports, "bare_except": [source[:m.start()].count("\n") + 1 for m in BARE_EXCEPT.finditer(source)]}


def read(project, rel: str) -> dict | None:
    """facts() plus `mapped` (see the module docstring)."""
    found = facts(project.root, rel)
    if found is not None:
        found["mapped"] = bool(project.test_module(rel) or project.pytest_target(rel))
    return found


def usage(root, files: list[str], names: set[str]) -> dict[str, set[str]]:
    """{name: the tracked .py/.js/.html files (tests left out) that mention it}."""
    found: dict[str, set[str]] = {n: set() for n in names}
    word = re.compile(r"[A-Za-z_]\w*")
    for rel in files:
        if not rel.endswith((".py", ".js", ".html")) or rel.startswith("node_modules/") or TESTS.search(rel):
            continue
        for name in names.intersection(word.findall(_read(root, rel))):
            found[name].add(rel)
    return found
