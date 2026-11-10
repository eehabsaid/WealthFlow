"""Fail if anything under ai/ depends on the WealthFlow ``core`` app.

Scans every .py file with the AST (imports, ``apps.get_model("core.X")``,
and string references such as ``"core.models"``). The scan is the proof that
ai/ can be copied into another Django project without WealthFlow.
"""
import ast
import re
from pathlib import Path

from django.test import SimpleTestCase

AI_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ("core",)  # host-specific top-level packages ai/ must not use
STRING_RE = re.compile(r"""^(?:%s)(?:[./]|$)""" % "|".join(FORBIDDEN))
GET_MODEL_RE = re.compile(r"""^(?:%s)\.\w+$""" % "|".join(FORBIDDEN))


def _is_forbidden_module(name: str) -> bool:
    return name.split(".")[0] in FORBIDDEN


MARKER = "ai-independence: ok"   # on the line: a deliberate mention (a stop word, a negative assertion)


def _is_test_file(path: Path) -> bool:
    return "tests" in path.parts or path.name.startswith("test_")


def scan_file(path: Path) -> list[str]:
    """Return human-readable violations found in one python file.

    Imports are checked everywhere; string references (app labels, dotted paths) only in production code,
    because test files may use host names as plain data."""
    try:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        tree = ast.parse(text)
    except SyntaxError as exc:  # pragma: no cover - reported as a violation
        return [f"{path}: syntax error {exc}"]
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_forbidden_module(alias.name):
                    found.append(f"{path}:{node.lineno} import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module and _is_forbidden_module(node.module):
                found.append(f"{path}:{node.lineno} from {node.module} import ...")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if _is_test_file(path) or MARKER in lines[node.lineno - 1]:
                continue
            if STRING_RE.match(node.value) and " " not in node.value:
                found.append(f"{path}:{node.lineno} string {node.value!r}")
    return found


def scan_tree(root: Path = AI_ROOT) -> list[str]:
    violations = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts or "node_modules" in path.parts:
            continue
        violations.extend(scan_file(path))
    return violations


class AIIndependenceScanTests(SimpleTestCase):
    def test_scanner_detects_import_forms(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "bad.py"   # not a tests path: strings count too
            sample.write_text(
                "from core.models import X\nimport core.services\n"
                "m = 'core.models.Expense'\nok = 'score.value'\n",
                encoding="utf-8",
            )
            hits = scan_file(sample)
        self.assertEqual(len(hits), 3, hits)

    def test_ai_has_no_core_dependency(self):
        violations = scan_tree()
        self.assertEqual(
            violations,
            [],
            f"{len(violations)} ai -> core references:\n" + "\n".join(violations[:60]),
        )
