"""End-to-end agent runs on a temp repo with a scripted fake model: plan -> approve -> execute -> verify/fix -> report, plus every stop rule."""

import json

import pytest

from ..engine.loop import Agent, AgentError
from ..settings.store import Settings
from .conftest import head
from .fakes import Approver, Scripted, edit, final, plan, tool


def agent(repo, replies, approver=None, **settings):
    s = {**Settings(repo).load(), **settings}
    return Agent(repo, Scripted(replies), s, approver or Approver(False))


def read(path):
    return tool("read_file", path=path)


GOOD_EDIT = [read("app/calc.py"), edit({"path": "app/calc.py", "replacements": [{"old": "a + b", "new": "a + b"}, ]}), ]


def test_plan_then_approve_then_execute_verified(repo):
    helper = "from app.calc import add\n\n\ndef add3(a, b, c):\n    return add(add(a, b), c)\n"
    a = agent(repo, [read("app/calc.py"), plan(files_add=["app/more.py"], files_edit=[], steps=[{"title": "add helper", "files": ["app/more.py"]}]),
                     edit({"path": "app/more.py", "content": helper}), final("added a helper"),
                     ])
    ledger = a.plan("add a helper for add")
    assert ledger.data["status"] == "awaiting_approval" and ledger.data["packages"][0]["status"] == "pending"
    assert not (repo.root / "app/more.py").exists()   # nothing is written before approval
    with pytest.raises(AgentError):
        a.execute(ledger.id)                                  # not approved yet
    a.approve(ledger.id)
    ledger = a.execute(ledger.id)
    d = ledger.data
    assert d["status"] == "completed" and d["files"]["app/more.py"]["state"] == "written"
    final_checks = [v for v in d["verification"] if v["label"] == "final"][0]["results"]
    assert {r["step"]: r["status"] for r in final_checks}["tests"] == "PASSED"
    text = (ledger.dir / "report.md").read_text()
    assert "Status: COMPLETED" in text and "Overall: VERIFIED" in text and "tests: PASSED" in text


def test_report_says_verified_only_when_everything_ran_and_passed(repo):
    cfg = json.loads((repo.agent_dir / "config.json").read_text())
    cfg["verify_steps"] = [cfg["verify_steps"][0]]
    cfg["e2e"] = {"paths": [], "command": ""}
    (repo.agent_dir / "config.json").write_text(json.dumps(cfg))
    repo.config = repo._load()
    a = agent(repo, [plan(files_add=["app/extra.py"], steps=[{"title": "add", "files": ["app/extra.py"]}], files_edit=[]),
                     edit({"path": "app/extra.py", "content": "VALUE = 1\n"}), final("x")])
    led = a.plan("add extra")
    a.approve(led.id)
    led = a.execute(led.id)
    text = (led.dir / "report.md").read_text()
    assert "Overall: VERIFIED" in text and "pyflakes: PASSED" in text


def test_failed_check_is_fixed_by_the_model(repo):
    broken = "import os\n\n\ndef f():\n    return 1\n"   # unused import: pyflakes fails
    a = agent(repo, [plan(files_add=["app/f.py"], files_edit=[], steps=[{"title": "add f", "files": ["app/f.py"]}]),
                     edit({"path": "app/f.py", "content": broken}), final("added"),
                     edit({"path": "app/f.py", "content": "def f():\n    return 1\n", "overwrite": True}), final("removed the unused import")])
    led = a.plan("add f")
    a.approve(led.id)
    led = a.execute(led.id)
    assert led.data["status"] == "completed"
    labels = [(v["label"], {r["step"]: r["status"] for r in v["results"]}["pyflakes"]) for v in led.data["verification"]]
    assert labels[0] == ("P1", "FAILED") and labels[-1][1] == "PASSED"


def test_three_failed_fix_attempts_stop_the_run(repo):
    bad = "import os\n"
    fixes = []
    for _ in range(6):
        fixes += [edit({"path": "app/f.py", "content": bad, "overwrite": True}), final("tried")]
    a = agent(repo, [plan(files_add=["app/f.py"], files_edit=[], steps=[{"title": "x", "files": ["app/f.py"]}]), edit({"path": "app/f.py", "content": bad}), final("x"), *fixes])
    led = a.plan("task")
    a.approve(led.id)
    led = a.execute(led.id)
    d = led.data
    assert d["status"] == "stopped" and "3 fix attempts" in d["stop_reason"]
    fix_calls = len([s for s in d["agent_summaries"] if s.get("fix")])
    assert fix_calls == 3                                  # exactly three fix attempts, then stop
    assert d["packages"][0]["status"] == "stopped"
    assert "Stopped: P1: 3 fix attempts" in (led.dir / "report.md").read_text()


def test_protected_file_is_never_written_without_approval_and_proposal_is_reported(repo):
    a = agent(repo, [plan(files_edit=["app/money.py", "app/calc.py"], steps=[{"title": "x", "files": ["app/money.py"]}]),
                     read("app/money.py"), edit({"path": "app/money.py", "replacements": [{"old": "1", "new": "2"}]}),
                     tool("note_proposal", path="app/money.py", text="change BALANCE to 2"), final("proposed the change"),
                     ], Approver(False))
    led = a.plan("change balance")
    assert "app/money.py" in led.data["plan"]["needs_owner_approval"]
    a.approve(led.id)
    led = a.execute(led.id)
    assert (repo.root / "app/money.py").read_text() == "BALANCE = 1\n"
    assert led.data["proposals"][0]["text"] == "change BALANCE to 2"
    assert any(not ap["approved"] for ap in led.data["approvals"])
    text = (led.dir / "report.md").read_text()
    assert "Protected-file change proposed for you: app/money.py" in text and "Refused/not approved" in text


def test_protected_file_changes_when_owner_approves(repo):
    a = agent(repo, [plan(files_edit=["app/money.py"], steps=[{"title": "x", "files": ["app/money.py"]}]), read("app/money.py"),
                     edit({"path": "app/money.py", "replacements": [{"old": "1", "new": "2"}]}), final("done")], Approver(True))
    led = a.plan("t")
    a.approve(led.id)
    a.execute(led.id)
    assert (repo.root / "app/money.py").read_text() == "BALANCE = 2\n"


def test_scope_change_outside_the_plan_is_refused(repo):
    a = agent(repo, [plan(), edit({"path": "app/util.py", "replacements": [{"old": "out = 0", "new": "out = 1"}]}), final("x")], Approver(False))
    led = a.plan("t")
    a.approve(led.id)
    a.execute(led.id)
    assert "out = 0" in (repo.root / "app/util.py").read_text()


def test_delete_and_rename_only_as_listed_in_the_plan(repo):
    a = agent(repo, [plan(files_edit=[], files_delete=["app/old.py"], files_rename=[{"from": "app/util.py", "to": "app/utils.py"}],
                          steps=[{"title": "tidy", "files": ["app/old.py", "app/util.py"]}]),
                     tool("delete_file", path="app/calc.py"), tool("delete_file", path="app/old.py"), tool("rename_file", **{"from": "app/util.py", "to": "app/utils.py"}),
                     tool("rename_file", **{"from": "app/calc.py", "to": "app/c.py"}), final("done")])
    led = a.plan("tidy")
    a.approve(led.id)
    led = a.execute(led.id)
    root = repo.root
    assert (root / "app/calc.py").exists() and not (root / "app/old.py").exists() and (root / "app/utils.py").exists() and not (root / "app/c.py").exists()
    assert led.data["files"]["app/old.py"]["state"] == "deleted"


def test_git_writes_cannot_happen_through_the_agent(git_repo):
    cmds = ["git commit --allow-empty -m x", "git push", "git reset --hard", "git stash", "git checkout -b z", "git clean -fd", "git branch q"]
    a = agent(git_repo, [plan(files_edit=[], files_add=["app/n.py"], steps=[{"title": "x", "files": ["app/n.py"]}]),
                         *[tool("run_command", command=c, reason="please") for c in cmds], tool("git", args=["status"]), final("done")], Approver(True))
    before = head(git_repo)
    led = a.plan("t")
    a.approve(led.id)
    a.execute(led.id)
    assert head(git_repo) == before
    import subprocess
    assert subprocess.run(["git", "branch"], cwd=git_repo.root, capture_output=True, text=True).stdout.split() == ["*", subprocess.run(
        ["git", "branch", "--show-current"], cwd=git_repo.root, capture_output=True, text=True).stdout.strip()]
    assert subprocess.run(["git", "stash", "list"], cwd=git_repo.root, capture_output=True, text=True).stdout == ""


def test_planning_phase_is_read_only(repo):
    a = agent(repo, [edit({"path": "app/new.py", "content": "X = 1\n"}), plan(files_add=["app/new.py"], files_edit=[])])
    led = a.plan("t")
    assert not (repo.root / "app/new.py").exists() and led.data["status"] == "awaiting_approval"
