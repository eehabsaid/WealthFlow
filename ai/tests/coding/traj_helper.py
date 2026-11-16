"""Real agent runs inside the throw-away project of ledger_helper: a real Agent with a scripted model writes tasks/<id>/ledger.json and events.jsonl exactly like
`python -m ai.dev_agent run` does, so the trajectory extractor is tested on what the agent really logs. Only the model and the verification commands are fakes."""

import json
import time
from pathlib import Path
from unittest.mock import patch

from ai.dev_agent.core.project import Project

from ai.dev_agent.engine import verify
from ai.dev_agent.engine.loop import Agent
from ai.dev_agent.settings.store import Settings
from ai.dev_agent.tests.fakes import Approver, Scripted, edit, plan, tool
from ai.tests.coding.ledger_helper import LedgerRepo

FILES = {
    "app/__init__.py": "",
    "app/calc.py": "def add(a, b):\n    return a + b\n",
    "app/util.py": "from app.calc import add\n\n\ndef total(xs):\n    out = 0\n    for x in xs:\n        out = add(out, x)\n    return out\n",
    "app/money.py": "BALANCE = 1\n",
}
PASS = [{"step": "tests", "status": "PASSED", "detail": ""}]
FAIL = [{"step": "tests", "status": "FAILED", "detail": "AssertionError: add(1, 2) != 3"}]
SUB = "def sub(a, b):\n    return a - b\n"
READ = tool("read_file", path="app/calc.py")
PLAN = plan(summary="add sub", steps=[{"title": "add sub", "files": ["app/calc.py"]}])
ADD_SUB = edit({"path": "app/calc.py", "replacements": [{"old": "    return a + b\n", "new": "    return a + b\n\n\ndef sub(a, b):\n    return a - b\n"}]})
QA_GOAL, PATCH_GOAL = "how does add work?", "add a sub function"


class TrajRepo(LedgerRepo):
    def setUp(self):
        super().setUp()
        for rel, text in FILES.items():
            self.write(rel, text)
        self.provider = None

    def agent(self, replies, approve=False) -> Agent:
        self.provider = Scripted(replies)
        return Agent(self.project, self.provider, Settings(self.project).load(), Approver(approve), events=True)

    def ask(self, question: str, replies: list):
        """A question: one `plan` phase that ends with `final`."""
        return self.agent(replies).plan(question)

    def patch_run(self, question: str, replies: list, checks=(PASS,), approve=False):
        """plan -> approve -> execute. `replies` are consumed in order by every phase; each verification call gets the next result list of `checks` (the last
        one repeats) - the agent loop, the logging and the ledger are all real."""
        agent = self.agent(replies, approve)
        ledger = agent.plan(question)
        queue = list(checks)
        with patch.object(verify, "run", lambda ctx, changed: queue.pop(0) if len(queue) > 1 else queue[0]):
            agent.approve(ledger.id)
            return agent.execute(ledger.id)

    def set_traj_config(self, **changes) -> None:
        path = self.root / "coding_agent" / "traj_training.json"
        path.write_text(json.dumps({**json.loads(path.read_text(encoding="utf-8")), **changes}), encoding="utf-8")


def scripted_runner(scripts: dict):
    """A stand-in for loop_eval.run_cli that keeps everything real except the model: it reads the model the evaluation pinned in the copy's agent_settings.json,
    answers from `scripts[model][goal]` (a list of replies) and drives the REAL Agent like `python -m ai.dev_agent run` does (plan; if a plan is waiting,
    approve and execute; a protected-file approval is refused as it is without a terminal). Verification commands pass."""
    def runner(root, goal, timeout):
        project = Project(root)
        model = json.loads((Path(root) / "coding_agent" / "agent_settings.json").read_text(encoding="utf-8"))["model"]
        agent = Agent(project, Scripted(scripts[model][goal]), Settings(project).load(), Approver(False), events=True)
        began = time.monotonic()
        ledger = agent.plan(goal)
        if ledger.data["status"] == "awaiting_approval":
            with patch.object(verify, "run", lambda ctx, changed: PASS):
                agent.approve(ledger.id)
                agent.execute(ledger.id)
        return {"returncode": 0, "timed_out": False, "seconds": time.monotonic() - began, "tail": ""}
    return runner


def _py(code: str) -> str:
    return code.rstrip("\n") + "\n" + "# padding\n" * 24   # the task list only draws on files of 25 to 185 lines


_HUGE = "def big(a, b):\n    total = a\n    total += b\n    total += 1\n    return total\n\n\ndef second(a):\n    return a\n"
TASK_FILES = {   # a small project with known gaps; `app/` maps to a test area, app/money.py is protected (see CONFIG of ledger_helper)
    "app/calc.py": _py("def add(a, b):\n    total = a\n    total += b\n    total += 0\n    return total\n\n\ndef scale(x, factor):\n    r = x\n    r *= factor\n    r += 0\n    return r\n"),
    "app/util.py": _py('"""Helpers."""\nfrom ai.beta import b\nfrom core.alpha import a\n\n\ndef combine(items):\n    out = []\n    for item in items:\n        out.append(a(item))\n    out.append(b())\n    return out\n'),
    "app/models.py": _py('class Box:\n    def __init__(self, size):\n        self.size = size\n\n    def volume(self):\n        return self.size ** 3\n\n\nclass Lid(Box):\n    """A lid."""\n\n    def fits(self, box):\n        return box.size == self.size\n'),
    "app/flow.py": _py("def run(job):\n    try:\n        job()\n    except:\n        return False\n    return True\n"),
    "app/extra.py": _py('def parse(text, sep):\n    parts = text.split(sep)\n    parts.reverse()\n    parts.append("")\n    return parts\n'),
    "app/views.py": _py("from app.calc import add\n\n\ndef render(request):\n    return add(1, 2)\n"),
    "app/salary_report.py": _py("def summary(rows, label):\n    out = []\n    for row in rows:\n        out.append((label, row))\n    return out\n\n\ndef detail(row):\n    return [row, row, row]\n"),
    "app/money.py": _py("BALANCE = 1\n"),
    "app/huge.py": _HUGE + "# line\n" * (183 - _HUGE.count("\n")),
    "app/tests/test_x.py": _py("def test_nothing():\n    assert True\n"),
    "other/unmapped.py": _py("def helper(a, b):\n    out = a\n    out += b\n    out += 1\n    return out\n\n\ndef more(a):\n    return a\n"),
    "static/js/widget.js": "function paintWidget(el, text) {\n  const node = el;\n  node.textContent = text;\n  return node;\n}\n\nfunction other(a) {\n  if (a) {\n    return 1;\n  }\n  return 2;\n}\n" + "// pad\n" * 24,
    "static/js/second.js": "function listItems(rows) {\n  const out = [];\n  for (const row of rows) {\n    out.push(row);\n  }\n  return out;\n}\n" + "// pad\n" * 24,
    "templates/home.html": "<script>paintWidget(el, 'x');</script>\n",
}
SMALL = {"qa": {"what_does": 1, "callers": 1, "module": 1}, "patch": {"hints": 1, "docstring": 1}}   # 3 + 2, the same mix as the real list


class TaskRepo(LedgerRepo):
    """LedgerRepo plus TASK_FILES, with `app/` mapped to a test area."""

    def setUp(self):
        super().setUp()
        for rel, text in TASK_FILES.items():
            self.write(rel, text)
        self.project = Project(self.root)
