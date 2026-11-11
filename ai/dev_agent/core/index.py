"""Repo index built from the source itself (AST for Python, a light scan for JS): files, classes, functions, models, imports, routes,
and who imports what. It stores file metadata so it can detect stale, renamed, modified and deleted files and refresh incrementally instead of
rebuilding on every request. Adapted from ai/services/coding/index.py, no Django."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from datetime import datetime, timezone

from ai.dev_agent.core.project import ALWAYS_EXCLUDE

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


class Index:
    def __init__(self, project):
        self.project = project
        self._stamp = None
        self._files: dict = {}
        self._state_path = self.project.agent_dir / ".index_state.json"
        self._state = self._load_state()

    def _load_state(self) -> dict:
        try:
            payload = json.loads(self._state_path.read_text(encoding="utf-8")) if self._state_path.exists() else {}
        except (OSError, ValueError):
            return {"version": INDEX_VERSION, "last_successful_update": None, "files": {}, "manifest": {}}
        if not isinstance(payload, dict):
            return {"version": INDEX_VERSION, "last_successful_update": None, "files": {}, "manifest": {}}
        payload.setdefault("version", INDEX_VERSION)
        payload.setdefault("files", {})
        payload.setdefault("manifest", {})
        payload.setdefault("last_successful_update", None)
        payload.setdefault("errors", [])
        return payload

    def _save_state(self) -> None:
        self.project.agent_dir.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps(self._state, indent=2, sort_keys=True), encoding="utf-8")

    def _walk(self):
        skip = ALWAYS_EXCLUDE | set(self.project.config["index_exclude"])
        for root_rel in self.project.config.get("agent_index_roots") or self.project.config["index_roots"]:
            base = self.project.root / root_rel
            if not base.exists():
                continue
            for folder, dirs, names in os.walk(base):
                dirs[:] = [d for d in dirs if d not in skip]
                for name in names:
                    if name.endswith(CODE_EXT):
                        yield os.path.join(folder, name)

    def _live_manifest(self) -> dict:
        manifest = {}
        for full in self._walk():
            try:
                st = os.stat(full)
            except OSError:
                continue
            rel = os.path.relpath(full, self.project.root).replace("\\", "/")
            if st.st_size <= MAX_BYTES:
                try:
                    with open(full, "rb") as handle:
                        digest = hashlib.sha256(handle.read()).hexdigest()
                except OSError:
                    digest = None
            else:
                digest = None
            manifest[rel] = {"mtime_ns": st.st_mtime_ns, "size": st.st_size, "sha256": digest}
        return manifest

    def _index_file(self, full: str, rel: str) -> dict:
        try:
            if os.path.getsize(full) > MAX_BYTES:
                return {"lines": 0, "classes": [], "functions": [], "models": {}, "imports": [], "routes": [], "sha256": None}
            with open(full, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            return {"lines": 0, "classes": [], "functions": [], "models": {}, "imports": [], "routes": [], "sha256": None}
        kind = "py" if rel.endswith(".py") else "js" if rel.endswith((".js", ".ts")) else "html"
        entry = _py(text) if kind == "py" else _js(text) if kind == "js" else _html(text)
        entry["sha256"] = _sha256(text)
        entry["path"] = rel
        return entry

    def detect_changes(self) -> dict:
        previous = self._state.get("manifest", {})
        current = self._live_manifest()
        added = sorted(path for path in current if path not in previous)
        removed = sorted(path for path in previous if path not in current)
        modified = sorted(
            path for path in current
            if path in previous and (
                previous[path].get("sha256") != current[path].get("sha256")
                or previous[path].get("mtime_ns") != current[path].get("mtime_ns")
                or previous[path].get("size") != current[path].get("size")
            )
        )
        old_by_hash = {meta.get("sha256"): path for path, meta in previous.items() if meta.get("sha256")}
        new_by_hash = {meta.get("sha256"): path for path, meta in current.items() if meta.get("sha256")}
        renamed = []
        for digest in sorted(set(old_by_hash) & set(new_by_hash)):
            old_path, new_path = old_by_hash[digest], new_by_hash[digest]
            if old_path != new_path and old_path in removed and new_path in added:
                renamed.append({"from": old_path, "to": new_path})
        stale = bool(added or removed or modified or renamed)
        return {"added": added, "modified": modified, "removed": removed, "renamed": renamed, "stale": stale}

    def refresh(self, *, force: bool = False) -> dict:
        changes = self.detect_changes() if not force else {"added": [], "modified": [], "removed": [], "renamed": [], "stale": True}
        if not force and not changes["stale"]:
            if not self._files:
                self._files = {path: self._index_file(os.path.join(self.project.root, path.replace("/", os.sep)), path) for path in self._state.get("files", {})}
            return {"status": "current", **changes, "updated_files": 0, "removed_files": 0}
        files = {}
        for full in self._walk():
            rel = os.path.relpath(full, self.project.root).replace("\\", "/")
            files[rel] = self._index_file(full, rel)
        self._files = files
        self._state["files"] = files
        self._state["manifest"] = self._live_manifest()
        self._state["last_successful_update"] = datetime.now(timezone.utc).isoformat()
        self._state["version"] = INDEX_VERSION
        self._state["errors"] = []
        self._save_state()
        removed_count = len(changes.get("removed", []))
        updated = len(changes.get("added", [])) + len(changes.get("modified", [])) + len(changes.get("renamed", []))
        return {"status": "updated", **changes, "updated_files": updated, "removed_files": removed_count}

    def rebuild(self) -> dict:
        return self.refresh(force=True)

    def ensure_current(self) -> dict:
        if not self._state.get("files") or not self._state.get("manifest") or self.is_stale():
            return self.refresh()
        return {"status": "current", "updated_files": 0, "removed_files": 0}

    def is_stale(self) -> bool:
        return self.detect_changes()["stale"]

    def status(self) -> dict:
        changes = self.detect_changes()
        entries = self._state.get("files", {}) or self._files
        symbol_count = sum(len(entry.get("classes", [])) + len(entry.get("functions", [])) for entry in entries.values())
        return {
            "status": "current" if not changes["stale"] else "stale",
            "index_version": self._state.get("version", INDEX_VERSION),
            "last_successful_update": self._state.get("last_successful_update"),
            "indexed_files": len(entries),
            "indexed_symbols": symbol_count,
            "updated_files": len(changes.get("added", []) + changes.get("modified", []) + changes.get("renamed", [])),
            "removed_files": len(changes.get("removed", [])),
            "requires_rebuild": False,
            "errors": self._state.get("errors", []),
            "changes": changes,
        }

    def get(self) -> dict:
        if self.is_stale() or not self._files:
            self.refresh()
        return self._files

    def callers(self, name: str) -> list[str]:
        """Files that import `name` (a module, class or function name)."""
        return sorted(p for p, e in self.get().items() if any(name in re.split(r"[./\\]", i) for i in e.get("imports", [])))

    def search(self, query: str, limit: int = 15) -> list[dict]:
        self.ensure_current()
        words = _words(query)
        rows = []
        for path, e in self.get().items():
            symbols = e.get("classes", []) + e.get("functions", []) + list(e.get("models", {}))
            score = 3 * len(words & _words(path.replace("/", " "))) + 2 * len(words & _words(" ".join(symbols))) + len(words & _words(" ".join(e.get("imports", []))))
            if score:
                rows.append({"path": path, "lines": e.get("lines", 0), "classes": e.get("classes", [])[:5], "functions": e.get("functions", [])[:8], "score": score})
        return sorted(rows, key=lambda r: (-r["score"], r["path"]))[:limit]
