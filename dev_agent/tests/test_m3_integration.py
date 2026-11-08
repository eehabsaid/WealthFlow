"""M3 end to end through the public surfaces: service restart after a crash, CLI memory commands, UI task with E2E, memory across two tasks."""

from ..cli import main
from ..engine import e2e
from ..ledger.ledger import Ledger
from ..memory import store
from .fakes import Scripted, edit, final, plan
from .test_m3_recovery import crash
from .test_service import idle, service
from .test_agent_flow import agent


def test_server_restart_after_a_crash_shows_the_task_as_stopped_and_resumable(repo):
    a = agent(repo, [plan(files_add=["app/new.py"], files_edit=[], steps=[{"title": "two", "files": ["app/new.py"]}])])
    led = a.plan("x")
    a.approve(led.id)
    crash(Ledger.load(repo, led.id))
    svc = service(repo, Scripted([edit({"path": "app/new.py", "content": "Z = 3\n"}), final("done")]))      # a new server process starts
    assert Ledger.load(repo, led.id).data["status"] == "stopped" and "Resume" in Ledger.load(repo, led.id).data["stop_reason"]
    assert svc.list_tasks()[0]["status"] == "stopped" and any("interrupted" in e.get("reason", "") for e in svc.log(led.id).after(0))
    svc.resume(led.id)
    assert idle(svc) and Ledger.load(repo, led.id).data["status"] == "completed"


def test_ui_task_runs_the_browser_suite_once_at_the_end_and_the_report_says_so(repo, monkeypatch):
    monkeypatch.setattr(e2e, "playwright_available", lambda: True)
    (repo.root / "scripts").mkdir(exist_ok=True)
    (repo.root / "scripts" / "run_full_e2e.py").write_text("print('browser suite ok')\n", encoding="utf-8")
    (repo.root / "static").mkdir(exist_ok=True)
    (repo.root / "static" / "a.js").write_text("var a = 1;\n", encoding="utf-8")
    a = agent(repo, [plan(files_edit=["static/a.js"], steps=[{"title": "ui", "files": ["static/a.js"]}], files_add=[]),
                     edit({"path": "static/a.js", "replacements": [{"old": "var a = 1;", "new": "var a = 2;"}]}), final("ui changed")])
    led = a.plan("change the ui")
    a.approve(led.id)
    led = a.execute(led.id)
    results = {r["step"]: r["status"] for v in led.data["verification"] for r in v["results"] if v["label"] == "final"}
    text = (led.dir / "report.md").read_text()
    assert led.data["status"] == "completed" and results["browser E2E"] == "PASSED"
    assert [r["status"] for v in led.data["verification"] if v["label"] != "final" for r in v["results"] if r["step"] == "browser E2E"] in ([], ["SKIPPED"])
    assert "browser E2E: PASSED" in text and "Browser E2E, real model" not in text


def test_ui_task_without_playwright_is_not_verified_and_the_report_says_why(repo, monkeypatch):
    monkeypatch.setattr(e2e, "playwright_available", lambda: False)
    (repo.root / "scripts").mkdir(exist_ok=True)
    (repo.root / "scripts" / "run_full_e2e.py").write_text("print('x')\n", encoding="utf-8")
    (repo.root / "static").mkdir(exist_ok=True)
    (repo.root / "static" / "b.js").write_text("var b = 1;\n", encoding="utf-8")
    a = agent(repo, [plan(files_edit=["static/b.js"], steps=[{"title": "ui", "files": ["static/b.js"]}], files_add=[]),
                     edit({"path": "static/b.js", "replacements": [{"old": "var b = 1;", "new": "var b = 2;"}]}), final("ui changed")])
    led = a.plan("change the ui")
    a.approve(led.id)
    text = (a.execute(led.id).dir / "report.md").read_text()
    assert "browser E2E: NOT RUN" in text and "Playwright is not installed" in text and "NOT VERIFIED" in text


def test_second_task_sees_what_the_first_one_learned(repo):
    a = agent(repo, [plan(files_add=["app/more.py"], files_edit=[], steps=[{"title": "add", "files": ["app/more.py"]}]), edit({"path": "app/more.py", "content": "Q = 1\n"}), final("ok")])
    first = a.plan("add more helper module")
    a.approve(first.id)
    a.execute(first.id)
    b = agent(repo, [final("answer")])
    b.plan("explain the more helper module")
    prompt = b.provider.calls[0][1][0]["content"]
    assert "Earlier tasks" in prompt and "add more helper module" in prompt


def test_cli_memory_show_add_forget(repo, capsys):
    root = ["--root", str(repo.root)]
    assert main([*root, "memory", "add", "lessons", "always run pyflakes"]) == 0
    assert main([*root, "memory", "show"]) == 0
    assert "always run pyflakes" in capsys.readouterr().out
    assert main([*root, "memory", "forget", "lessons", "pyflakes"]) == 0 and store.entries(repo, "lessons") == []
    assert main([*root, "memory", "add", "lessons", "password=abc"]) != 0
