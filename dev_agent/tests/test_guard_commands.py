from pathlib import Path

import pytest

from ..guard.commands import CommandError, classify, exe_name, split_command

ROOT = Path("/proj")
CMDS = {"allow": [["python", "manage.py", "check"], ["python", "-m", "pytest"], ["npx", "eslint"]], "ask": [["python", "manage.py", "migrate"]],
        "deny": [["python", "manage.py", "flush"]]}


def c(text, windows=False):
    return classify(split_command(text, windows), ROOT, CMDS)


@pytest.mark.parametrize("cmd", [
    "git commit -m x", "git push", "git push origin main", "git reset --hard", "git checkout main", "git checkout -- f.py", "git clean -fd",
    "git stash", "git stash pop", "git branch new", "git branch -D x", "git switch -c x", "git restore f", "git add .", "git rm f", "git mv a b",
    "git merge x", "git rebase x", "git cherry-pick x", "git revert x", "git tag v1", "git apply p.diff", "git am p", "git pull", "git fetch",
    "git clone x", "git init", "git config user.name x", "git remote add o u", "git gc", "git worktree add x", "git submodule update", "git update-ref x y",
    "git symbolic-ref HEAD x", "git bisect start", "git reflog expire --all", "git filter-branch", "git format-patch -1", "git commit-tree x",
    "git -c core.pager=evil log", "git -C other status", "git --git-dir=x status", "git --work-tree=x status", "git log --output=out.txt",
    "git diff --output=out.patch", "git diff --ext-diff", "git diff --no-index a b", "git show -O orders", "git grep -O foo", "git log --open-files-in-pager=sh",
    "git", "git --version-bogus", "GIT commit", "git.exe commit", "git-receive-pack x", "git-lfs pull",
])
def test_git_writes_are_all_denied(cmd):
    assert c(cmd).action == "deny", cmd


@pytest.mark.parametrize("cmd", ["git status", "git diff", "git diff --stat HEAD~1", "git log --oneline -5", "git show HEAD:app/x.py", "git blame app/x.py",
                                 "git ls-files", "git rev-parse HEAD", "git --no-pager diff", "git grep -n foo -- app", "GIT status"])
def test_git_read_only_is_allowed(cmd):
    assert c(cmd).action == "allow", cmd


def test_git_reads_with_windows_exe_name():
    assert classify(["git.exe", "status"], ROOT, CMDS).action == "allow"
    assert classify([r"C:\Program Files\Git\cmd\git.exe", "log"], ROOT, CMDS).action == "allow"


@pytest.mark.parametrize("cmd", ["bash -c 'git commit'", "sh -c x", "cmd /c git commit", "powershell -Command x", "pwsh x", "wsl git commit", "env git commit",
                                 "sudo ls", "xargs rm", "gh pr create", "eval x", "nohup x"])
def test_wrappers_that_hide_commands_are_denied(cmd):
    assert c(cmd).action == "deny", cmd


@pytest.mark.parametrize("cmd", ["python manage.py check && git commit", "ls | sh", "echo x > f", "a ; b", "x & y", "x 2>&1"])
def test_shell_operators_denied(cmd):
    assert c(cmd).action == "deny"


def test_multiline_and_unbalanced_rejected():
    for bad in ("a\ngit commit", "a\rb", "python 'x"):
        with pytest.raises(CommandError):
            split_command(bad, False)


def test_whitelist_allows_and_matches_by_prefix_only():
    assert c("python manage.py check").action == "allow"
    assert c("python3.12 manage.py check --deploy").action == "allow"
    assert c("py manage.py check").action == "allow"
    assert c("python -m pytest tests -q").action == "allow"
    assert c("npx eslint static/js/a.js").action == "allow"
    assert c("python manage.py checkx").action == "ask"
    assert c("python manage.py migrate").action == "ask"
    assert c("python evil.py").action == "ask"


def test_project_deny_list_beats_everything():
    assert c("python manage.py flush").action == "deny"


@pytest.mark.parametrize("cmd", ["rm -rf x", "del f", "rmdir /s x", "mv a b", "curl http://x", "pip install x", "python -m pip install x", "npm install", "npx cowsay",
                                 "winget install x", "taskkill /F", "shutdown now", "reg add x"])
def test_destructive_installs_and_system_commands_ask(cmd):
    assert c(cmd).action == "ask", cmd


@pytest.mark.parametrize("cmd", ["python -m pytest ../other", "python -m pytest /etc", "python -m pytest C:/x", r"python -m pytest C:\x", "python -m pytest ~/x",
                                 "python -m pytest --rootdir=/x", "python -m pytest http://x/y"])
def test_arguments_outside_project_need_approval(cmd):
    assert c(cmd).action == "ask", cmd


def test_inside_project_absolute_path_is_fine(tmp_path):
    (tmp_path / "t.py").write_text("")
    d = classify(["python", "-m", "pytest", str(tmp_path / "t.py")], tmp_path, CMDS)
    assert d.action == "allow"


def test_windows_split_keeps_backslashes_and_quotes():
    assert split_command(r'python -m pytest "tests\unit" -k x', True) == ["python", "-m", "pytest", r"tests\unit", "-k", "x"]
    assert split_command(r"npx eslint static\js\a.js", True) == ["npx", "eslint", r"static\js\a.js"]


def test_exe_name_normalisation():
    assert exe_name("Python3.12.EXE") == "python" and exe_name(r"C:\x\npx.cmd") == "npx" and exe_name("/usr/bin/git") == "git"


def test_windows_style_paths_to_git_and_cmd():
    assert c(r'"C:\Program Files\Git\bin\git.exe" push', True).action == "deny"
    assert c(r'"C:\Program Files\Git\bin\git.exe" status', True).action == "allow"
    assert c(r"C:\Windows\System32\cmd.exe /c dir", True).action == "deny"
    assert c(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -c x", True).action == "deny"


def test_flags_that_rewrite_files_always_ask():
    cmds = {"allow": [["npx", "prettier"], ["npx", "eslint"]], "ask_args": ["--fix", "--write"]}
    for text in ("npx prettier --write a.js", "npx eslint --fix a.js"):
        assert classify(split_command(text, False), ROOT, cmds).action == "ask"
    assert classify(split_command("npx prettier --check a.js", False), ROOT, cmds).action == "allow"
