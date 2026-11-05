import ast
import pathlib
import subprocess
import sys

from .. import cli
from ..engine import report
from ..ledger.ledger import Ledger

PKG = pathlib.Path(__file__).resolve().parents[1]


def test_dev_agent_never_imports_django_or_wealthflow_code():
    bad = []
    for path in PKG.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) and node.level == 0 else []
            bad += [f"{path.name}: {n}" for n in names if n.split(".")[0] in ("django", "core", "wealthflow")]
    assert bad == []


def test_importing_the_agent_does_not_load_django():
    code = "import sys, dev_agent.cli, dev_agent.engine.loop; sys.exit(1 if any(m == 'django' or m.startswith('django.') for m in sys.modules) else 0)"
    assert subprocess.run([sys.executable, "-c", code], cwd=PKG.parent).returncode == 0


def test_cli_settings_status_and_keys(repo, capsys):
    assert cli.main(["--root", str(repo.root), "settings", "set", "model", "qwen2.5-coder"]) == 0
    assert "qwen2.5-coder" in capsys.readouterr().out
    assert cli.main(["--root", str(repo.root), "settings", "set", "nope", "x"]) == 2
    assert "unknown setting" in capsys.readouterr().err
    Ledger.create(repo, "demo task")
    assert cli.main(["--root", str(repo.root), "status"]) == 0
    assert "demo task" in capsys.readouterr().out
    assert cli.main(["--root", str(repo.root), "status", "missing"]) == 2


def test_cli_run_without_model_or_key_fails_with_a_clear_message(repo, capsys):
    assert cli.main(["--root", str(repo.root), "plan", "do something"]) == 2
    assert "no model chosen" in capsys.readouterr().err


def test_find_root_walks_up_to_config(repo):
    deep = repo.root / "app"
    assert cli.find_root(deep) == repo.root


def test_status_report_for_a_fresh_ledger_does_not_claim_verified(repo):
    text = report.build(Ledger.create(repo, "x"))
    assert "NOT VERIFIED" in text and "Overall: VERIFIED" not in text
