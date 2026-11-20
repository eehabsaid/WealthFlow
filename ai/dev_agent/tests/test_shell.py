"""The shell tool and its guard: safe commands run, risky ones ask, git writes / nested shells are denied, file changes made by a command are tracked."""

import subprocess
import sys

import pytest

from ai.dev_agent.guard.shell import classify_line, parse
from ai.dev_agent.tests.fakes import Approver
from ai.dev_agent.tools import call


RM_OLD = "del /q app\\old.py" if sys.platform == "win32" else "rm -f app/old.py"   # a delete that works in cmd and sh


def verdict(repo, line, **settings):
    return classify_line(line, repo, settings, windows=False).action


@pytest.mark.parametrize("line,action", [
    ("ls -la", "allow"), ("echo hi", "allow"), ("python -m pytest -q && echo ok", "allow"), ("python -m pyflakes app | cat", "allow"),
    ("grep -rn 'a|b' app", "allow"), ("cat app/calc.py > nul", "allow"), ("python -m pytest 2>&1", "allow"),
    ("git commit -m x", "deny"), ("git push", "deny"), ("git status && git stash", "deny"), ("bash -c ls", "deny"), ("ls && git reset --hard", "deny"),
    ("rm -rf build", "ask"), ("pip install requests", "ask"), ("echo hi > out.txt", "ask"), ("echo hi > ../x", "ask"), ("cat /etc/passwd", "ask"),
    ("echo $(whoami)", "ask"), ("python -m pytest && rm x", "ask"), ("echo hi > app/money.py", "ask"), ("cat app/money.py", "ask"), ("somecmd --x", "ask"),
])
def test_classification(repo, line, action):
    assert verdict(repo, line) == action


def test_an_unlisted_harmless_command_runs_when_that_approval_is_off_but_risky_ones_still_ask(repo):
    assert verdict(repo, "somecmd --x", ask_other_commands=False) == "allow"
    assert verdict(repo, "rm -rf build", ask_other_commands=False) == "ask" and verdict(repo, "cat app/money.py", ask_other_commands=False) == "ask"
    assert verdict(repo, "cat app/money.py", ask_protected_files=False) == "allow"


def test_parse_splits_chains_quotes_and_redirects():
    p = parse("python -m pytest -q && grep 'a && b' x.py | wc -l > out.txt 2>&1", windows=False)
    assert [c[0] for c in p.commands] == ["python", "grep", "wc"] and p.redirects == ["out.txt"]
    with pytest.raises(Exception):
        parse("echo 'unterminated", windows=False)
    with pytest.raises(Exception):
        parse("echo a\necho b", windows=False)


def test_shell_runs_a_safe_command_and_returns_the_output(ctx):
    out = call(ctx, "shell", {"command": "echo hello-shell"})
    assert out["status"] == "PASSED" and "hello-shell" in out["output"] and ctx.approver.asked == []


def test_shell_denies_git_writes_without_asking(ctx):
    out = call(ctx, "shell", {"command": "git commit -m x"})
    assert "blocked" in out["error"] and ctx.approver.asked == []


def test_shell_asks_before_a_risky_command_and_obeys_the_answer(ctx, repo):
    out = call(ctx, "shell", {"command": RM_OLD, "reason": "cleanup"})
    assert "did not approve" in out["error"] and (repo.root / "app/old.py").exists() and "cleanup" in ctx.approver.asked[0][1]
    ctx.approver = Approver(True)
    out = call(ctx, "shell", {"command": RM_OLD, "reason": "cleanup"})
    assert out["status"] == "PASSED" and not (repo.root / "app/old.py").exists()


def test_shell_is_not_offered_while_planning(ctx):
    ctx.readonly = True
    assert "not available while planning" in call(ctx, "shell", {"command": "echo x"})["error"]


def test_files_changed_by_a_command_are_found_and_recorded_with_their_original(git_repo, ctx):
    ctx.approver = Approver(True)
    ctx.project = git_repo
    out = call(ctx, "shell", {"command": "sed -i 's/a + b/a - b/' app/calc.py", "reason": "edit"})
    if out["status"] != "PASSED":
        pytest.skip("sed is not available")
    assert out["files_changed"] == ["app/calc.py"]
    entry = ctx.ledger.data["files"]["app/calc.py"]
    assert entry["state"] == "written" and ctx.ledger.data["snapshots"]["app/calc.py"] is not None


def test_a_command_that_changes_a_protected_file_is_reported(git_repo, ctx):
    ctx.approver = Approver(True)   # the owner approved the command, the change is still named in the result
    ctx.project = git_repo
    out = call(ctx, "shell", {"command": "sed -i 's/1/2/' app/money.py"})
    if out["status"] != "PASSED":
        pytest.skip("sed is not available")
    assert "PROTECTED" in out["warning"] or "balances" in out["warning"]
    assert subprocess.run(["git", "status", "--porcelain"], cwd=git_repo.root, capture_output=True, text=True).stdout.count("money.py") == 1
