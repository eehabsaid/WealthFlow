import sys

import pytest

from ..tools import call, runner
from .conftest import head


def run_cmd(ctx, command, reason=""):
    return call(ctx, "run_command", {"command": command, "reason": reason})


def test_whitelisted_command_runs_and_passes(ctx):
    res = run_cmd(ctx, "python -m pytest -q -p no:cacheprovider tests/test_calc.py")
    assert res["status"] == "PASSED" and "1 passed" in res["output"]


def test_failing_command_is_reported_failed(ctx):
    (ctx.project.root / "tests/test_calc.py").write_text("def test_x():\n    assert False\n")
    res = run_cmd(ctx, "python -m pytest -q -p no:cacheprovider tests")
    assert res["status"] == "FAILED" and res["exit_code"] != 0 and "assert" in res["output"]


def test_non_whitelisted_needs_approval_and_denied_without_it(ctx):
    res = run_cmd(ctx, "python -c print(1)", "check")
    assert "did not approve" in res["error"] and ctx.approver.asked
    ctx.approver.answer = True
    ctx.approved.clear()
    assert run_cmd(ctx, "python -c print(1)", "check")["status"] == "PASSED"


def test_pip_install_asks_and_is_not_run_without_approval(ctx):
    assert "did not approve" in run_cmd(ctx, "python -m pip install requests", "need it")["error"]


def test_approval_never_overrides_a_deny(ctx):
    ctx.approver.answer = True
    for cmd in ("git commit -m x", "git push", "bash -c ls", "python -m pytest && ls"):
        assert "blocked" in run_cmd(ctx, cmd, "please")["error"], cmd
    assert ctx.approver.asked == []


def test_timeout_kills_the_process_tree(ctx):
    ctx.settings = {**ctx.settings, "command_timeout_s": 1}
    ctx.approver.answer = True
    res = run_cmd(ctx, 'python -c "import time; time.sleep(30)"', "sleep")
    assert res["timed_out"] and res["status"] == "FAILED" and res["duration_s"] < 15


def test_missing_executable_is_not_run(ctx):
    ctx.approver.answer = True
    assert run_cmd(ctx, "definitely-not-a-tool --x", "x")["status"] == "NOT RUN"


def test_output_is_clipped_to_the_budget(ctx):
    ctx.approver.answer = True
    res = run_cmd(ctx, 'python -c "print(\'x\' * 100000)"', "big")
    assert len(res["output"]) <= ctx.settings["max_tool_result_chars"] + 100


def test_run_tests_maps_files_to_modules(ctx):
    assert call(ctx, "run_tests", {"files": ["app/calc.py"]})["status"] == "PASSED"
    assert "no test module" in call(ctx, "run_tests", {"files": ["static/a.js"]})["error"]


def test_python_means_the_running_interpreter():
    assert runner.resolve_exe("python3.12") == sys.executable and runner.resolve_exe("py") == sys.executable


def test_batch_launcher_metacharacters_are_blocked(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.shutil, "which", lambda a: "C:\\x\\npx.cmd")
    assert runner.run(["npx", "a&b"], tmp_path, 5)["status"] == "NOT RUN"


GIT_WRITES = ["commit -m x --allow-empty", "reset --hard HEAD~0", "checkout -b x", "stash", "branch x", "clean -fd", "push origin main", "add -A", "tag v1",
              "rebase main", "merge main", "switch -c y", "restore app/calc.py", "rm app/calc.py"]


@pytest.mark.parametrize("sub", GIT_WRITES)
def test_git_tool_blocks_every_write_and_the_repo_is_untouched(git_repo, sub):
    from ..core.index import Index
    from ..settings.store import Settings
    from ..tools import ToolContext
    c = ToolContext(git_repo, Settings(git_repo).load(), Index(git_repo), None, __import__("dev_agent.tests.fakes", fromlist=["Approver"]).Approver(True), None, False)
    before = head(git_repo)
    res = call(c, "git", {"args": sub.split()})
    assert "blocked" in res["error"]
    assert head(git_repo) == before and (git_repo.root / "app/calc.py").exists()
    for cmd in (f"git {sub}",):
        assert "blocked" in call(c, "run_command", {"command": cmd})["error"]


def test_git_read_commands_work(git_repo):
    from ..core.index import Index
    from ..settings.store import Settings
    from ..tools import ToolContext
    c = ToolContext(git_repo, Settings(git_repo).load(), Index(git_repo), None, None, None, False)
    (git_repo.root / "app/calc.py").write_text("changed = 1\n")
    assert "calc.py" in call(c, "git", {"args": ["status", "--short"]})["output"]
    assert "changed" in call(c, "git", {"args": ["diff"]})["output"]
    assert "init" in call(c, "git", {"args": ["log", "--oneline"]})["output"]
    assert call(c, "git", {"args": "status"})["error"].startswith("`args` must be a list")
