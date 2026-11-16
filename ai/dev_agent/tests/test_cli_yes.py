"""`run --yes` / `execute --yes`: the plan is approved without a question, so a batch of tasks never waits for a person. Nothing else is auto-approved: a protected file
still needs the answer typed in a terminal, and with no terminal (a batch) it is refused. Without --yes the question is still asked."""

import builtins

from ai.dev_agent import cli
from ai.dev_agent.engine.loop import Agent
from ai.dev_agent.ledger.ledger import Ledger
from ai.dev_agent.settings.store import Settings
from ai.dev_agent.tests.fakes import Scripted, edit, final, plan

NEW = [plan(files_add=["app/new.py"], files_edit=[], steps=[{"title": "add it", "files": ["app/new.py"]}]), edit({"path": "app/new.py", "content": "Z = 3\n"}), final("done")]
MONEY = [plan(files_add=[], files_edit=["app/money.py"], steps=[{"title": "change it", "files": ["app/money.py"]}]),
         edit({"path": "app/money.py", "replacements": [{"old": "BALANCE = 1", "new": "BALANCE = 2"}]}), final("done")]


def drive(repo, monkeypatch, replies, argv, typed=()):
    """cli.main with a scripted model and the real console approver. `typed` are the answers a person would type; asking more often than that fails the test."""
    agent = Agent(repo, Scripted(replies), Settings(repo).load(), cli.ConsoleApprover(), cli._emit, events=True)
    monkeypatch.setattr(cli, "_agent", lambda project, with_keys=True: agent)
    answers, asked = iter(typed), []

    def fake_input(prompt=""):
        asked.append(prompt.strip())
        try:
            return next(answers)
        except StopIteration:
            raise AssertionError(f"the command asked: {prompt!r}") from None

    monkeypatch.setattr(builtins, "input", fake_input)
    return cli.main(["--root", str(repo.root), *argv]), asked


def status(repo):
    return Ledger.load(repo, Ledger.list_ids(repo)[0]).data["status"]


def test_run_with_yes_approves_the_plan_executes_it_and_never_asks(repo, monkeypatch, capsys):
    code, asked = drive(repo, monkeypatch, NEW, ["run", "--yes", "add a file"])
    assert (code, asked, status(repo)) == (0, [], "completed")
    assert (repo.root / "app/new.py").read_text(encoding="utf-8") == "Z = 3\n"
    assert "Plan approved automatically (--yes)." in capsys.readouterr().out


def test_run_without_yes_still_asks_and_a_no_runs_nothing(repo, monkeypatch):
    code, asked = drive(repo, monkeypatch, NEW[:1], ["run", "add a file"], typed=["n"])
    assert (code, len(asked), status(repo)) == (0, 1, "awaiting_approval") and not (repo.root / "app/new.py").exists()


def test_run_without_yes_runs_the_plan_when_a_person_types_y(repo, monkeypatch):
    code, asked = drive(repo, monkeypatch, NEW, ["run", "add a file"], typed=["y"])
    assert (code, len(asked), status(repo)) == (0, 1, "completed")


def test_execute_with_yes_approves_a_waiting_plan_without_asking(repo, monkeypatch):
    assert drive(repo, monkeypatch, NEW[:1], ["plan", "add a file"])[0] == 0
    task_id = Ledger.list_ids(repo)[0]
    assert status(repo) == "awaiting_approval"
    monkeypatch.setattr(cli, "_agent", lambda project, with_keys=True: Agent(repo, Scripted(NEW[1:]), Settings(repo).load(), cli.ConsoleApprover(), cli._emit, events=True))
    monkeypatch.setattr(builtins, "input", lambda prompt="": (_ for _ in ()).throw(AssertionError(f"the command asked: {prompt!r}")))
    assert cli.main(["--root", str(repo.root), "execute", "--yes", task_id]) == 0
    assert status(repo) == "completed"


def test_yes_approves_the_plan_only_a_protected_file_is_still_refused_without_a_terminal(repo, monkeypatch, capsys):
    before = (repo.root / "app/money.py").read_text(encoding="utf-8")
    code, asked = drive(repo, monkeypatch, MONEY, ["run", "--yes", "change the balance"])
    assert asked == [], "no question at all: --yes answers the plan, and the protected file is refused because there is no terminal"
    assert (repo.root / "app/money.py").read_text(encoding="utf-8") == before
    assert "[not approved, no terminal]" in capsys.readouterr().out
