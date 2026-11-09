import json
import shutil
import subprocess

import pytest

from ai.dev_agent.core.index import Index
from ai.dev_agent.core.project import Project
from ai.dev_agent.ledger.ledger import Ledger
from ai.dev_agent.ledger.plan import PlanScope
from ai.dev_agent.settings.store import Settings
from ai.dev_agent.tools import ToolContext
from ai.dev_agent.tests.browserfix import browser, page
from ai.dev_agent.tests.fakes import Approver

__all__ = ["browser", "page"]   # Playwright fixtures for the browser tests

FILES = {
    "conftest.py": "",
    "app/__init__.py": "",
    "app/calc.py": "def add(a, b):\n    return a + b\n",
    "app/util.py": "from app.calc import add\n\n\ndef total(xs):\n    out = 0\n    for x in xs:\n        out = add(out, x)\n    return out\n",
    "app/money.py": "BALANCE = 1\n",
    "app/old.py": "OLD = 1\n",
    "tests/test_calc.py": "from app.calc import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n",
    ".env": "KEY=secret\n",
}
CONFIG = {
    "max_file_lines": 50,
    "protected": [{"pattern": "app/money.py", "reason": "balances"}],
    "forbidden": ["*/migrations/*.py", "db.sqlite3"],
    "test_areas": {"app": "tests/test_calc.py"},
    "test_command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "{modules}"],
    "commands": {"allow": [["python", "-m", "pytest"], ["python", "-m", "pyflakes"]]},
    "verify_steps": [{"name": "pyflakes", "argv": ["python", "-m", "pyflakes", "{files}"], "ext": [".py"]},
                     {"name": "tests", "argv": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "{modules}"]}],
    "e2e": {"paths": ["static/*"], "command": "scripts/run_full_e2e.py"},
}
PLAN = {"files_add": ["app/new.py", "tests/test_new.py"], "files_edit": ["app/calc.py", "app/util.py", "app/money.py"], "files_delete": ["app/old.py"],
        "files_rename": [{"from": "app/util.py", "to": "app/utils.py"}]}


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    for rel, text in FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    (root / "coding_agent").mkdir()
    (root / "coding_agent" / "config.json").write_text(json.dumps(CONFIG), encoding="utf-8")
    return Project(root)


@pytest.fixture
def ctx(repo):
    ledger = Ledger.create(repo, "test task")
    return ToolContext(repo, Settings(repo).load(), Index(repo), ledger, Approver(False), PlanScope({**{"files_add": [], "files_edit": [], "files_delete": [],
                       "files_rename": []}, **PLAN}), False, "P1", {}, set())


@pytest.fixture
def git_repo(repo):
    if not shutil.which("git"):
        pytest.skip("git is not installed")
    run = lambda *a: subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=repo.root, check=True, capture_output=True)  # noqa: E731
    run("init", "-q")
    run("add", "-A")
    run("commit", "-q", "-m", "init")
    return repo


def head(repo) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo.root, capture_output=True, text=True, check=True).stdout.strip()
