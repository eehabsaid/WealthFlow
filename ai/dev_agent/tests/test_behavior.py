"""Settings > Behavior: the approval switches, deep search, quick mode and light verification. Every switch keeps the strict behaviour when it is not touched."""

import pytest

from ai.dev_agent.engine import verify
from ai.dev_agent.settings import behavior
from ai.dev_agent.settings.store import FLAGS, Settings, SettingsError
from ai.dev_agent.tests.fakes import Scripted, edit, final, plan
from ai.dev_agent.tests.test_service import idle, service
from ai.dev_agent.tools import call


def off(ctx, *keys):
    ctx.settings = {**ctx.settings, **{k: False for k in keys}}


def test_defaults_keep_the_strict_behaviour(repo):
    data = Settings(repo).load()
    assert [data[k] for k in FLAGS] == [True, True, True, True, False, False, False]


def test_apply_saves_switches_and_reports_what_changed(repo):
    out = behavior.apply(repo, {"require_plan_approval": False, "deep_search": True, "ask_protected_files": True})
    assert [c["key"] for c in out["changed"]] == ["require_plan_approval", "deep_search"]
    assert Settings(repo).load()["require_plan_approval"] is False and {v["key"] for v in out["values"]} == set(FLAGS)


@pytest.mark.parametrize("values", [{}, {"nope": True}, {"deep_search": "yes"}, {"deep_search": 1}])
def test_apply_refuses_bad_input_and_changes_nothing(repo, values):
    with pytest.raises(SettingsError):
        behavior.apply(repo, values)
    assert Settings(repo).load()["deep_search"] is False


def test_the_settings_command_accepts_true_false(repo):
    assert Settings(repo).set("quick_mode", "true")["quick_mode"] is True


def test_a_file_outside_the_plan_asks_unless_that_approval_is_off(ctx):
    assert ctx.allow_write("app/extra.py", "create")[0] is False and len(ctx.approver.asked) == 1
    off(ctx, "ask_outside_plan")
    assert ctx.allow_write("app/extra.py", "create") == (True, "") and len(ctx.approver.asked) == 1


def test_a_protected_file_in_the_plan_asks_unless_that_approval_is_off(ctx):
    assert ctx.allow_write("app/money.py", "edit")[0] is False
    off(ctx, "ask_protected_files")
    assert ctx.allow_write("app/money.py", "edit") == (True, "")


def test_turning_off_outside_plan_does_not_unprotect_protected_files(ctx):
    ctx.scope.write.discard("app/money.py")
    off(ctx, "ask_outside_plan")
    assert ctx.allow_write("app/money.py", "edit")[0] is False   # still asks: protected


def test_deleting_outside_the_plan_always_asks_never_denies(ctx):
    ok, why = ctx.allow_write("app/calc.py", "delete")
    assert not ok and "not listed" in why and len(ctx.approver.asked) == 1   # asked; the approver said no
    off(ctx, "ask_outside_plan")
    ok, why = ctx.allow_write("app/calc.py", "delete")
    assert not ok and len(ctx.approver.asked) == 2
    ctx.approver.answer = True
    assert ctx.allow_write("app/calc.py", "delete") == (True, "")


def test_forbidden_and_secret_files_stay_blocked_with_every_switch_off(ctx):
    off(ctx, "ask_outside_plan", "ask_protected_files", "ask_other_commands")
    assert ctx.allow_write(".env", "edit")[0] is False and ctx.allow_write("db.sqlite3", "edit")[0] is False
    assert ctx.allow_write("coding_agent/config.json", "edit")[0] is False


def test_a_command_missing_from_the_allow_list_asks_unless_that_approval_is_off(ctx):
    res = call(ctx, "run_command", {"command": "python --version"})
    assert "did not approve" in res["error"]
    off(ctx, "ask_other_commands")
    res = call(ctx, "run_command", {"command": "python --version"})
    assert "error" not in res or not res["error"]
    assert res["status"] in ("PASSED", "FAILED")


def test_dangerous_commands_still_ask_or_stay_blocked_with_the_switch_off(ctx):
    off(ctx, "ask_other_commands")
    assert "did not approve" in call(ctx, "run_command", {"command": "rm app/old.py"})["error"]
    assert "did not approve" in call(ctx, "run_command", {"command": "pip install requests"})["error"]
    assert "blocked" in call(ctx, "run_command", {"command": "git push"})["error"]
    assert "blocked" in call(ctx, "run_command", {"command": "bash -c ls"})["error"]


def test_deep_search_reads_more_lines_and_returns_more_matches(ctx, repo):
    (repo.root / "app/long.py").write_text("".join(f"x{n} = {n}\n" for n in range(1500)), encoding="utf-8")
    assert call(ctx, "read_file", {"path": "app/long.py"})["end"] == 400
    ctx.settings = {**ctx.settings, "deep_search": True}
    assert call(ctx, "read_file", {"path": "app/long.py"})["end"] == 1200
    ctx.settings = {**ctx.settings, "deep_search": False}
    assert len(call(ctx, "grep", {"pattern": "^x", "glob": "app/long.py", "max_results": 500})["matches"]) == 200
    ctx.settings = {**ctx.settings, "deep_search": True}
    assert len(call(ctx, "grep", {"pattern": "^x", "glob": "app/long.py", "max_results": 500})["matches"]) == 500


def test_light_verification_skips_the_line_limit_and_mapping_and_says_so(ctx, repo):
    (repo.root / "app/big.py").write_text("".join(f"v{n} = {n}\n" for n in range(80)), encoding="utf-8")
    rows = {r["step"]: r for r in verify.run(ctx, ["app/big.py"])}
    assert rows["line limit (50)"]["status"] == "FAILED"
    ctx.settings = {**ctx.settings, "light_verification": True}
    rows = {r["step"]: r for r in verify.run(ctx, ["app/big.py"])}
    assert rows["line limit (50)"]["status"] == "SKIPPED" and "light verification" in rows["line limit (50)"]["detail"]
    assert rows["test mapping"]["status"] == "SKIPPED" and rows["pyflakes"]["status"] == "PASSED"


NEW = plan(files_add=["app/more.py"], files_edit=[], steps=[{"title": "add", "files": ["app/more.py"]}])


def test_with_plan_approval_off_the_task_runs_at_once_without_a_planning_phase(repo):
    behavior.apply(repo, {"require_plan_approval": False})
    svc = service(repo, Scripted([edit({"path": "app/more.py", "content": "X = 1\n"}), final("done")]))
    task_id = svc.start_task("add more")
    assert idle(svc)
    d = svc.ledger(task_id).data
    assert d["status"] == "completed" and (repo.root / "app/more.py").exists()
    assert any(a["kind"] == "plan" and a["approved"] and "no planning phase" in a["message"] for a in d["approvals"]) and d["plan"]["direct"]


def test_with_plan_approval_on_the_task_waits(repo):
    svc = service(repo, Scripted([NEW]))
    task_id = svc.start_task("add more")
    assert idle(svc) and svc.ledger(task_id).data["status"] == "awaiting_approval"


def test_quick_mode_with_approval_on_still_waits_for_you(repo):
    behavior.apply(repo, {"quick_mode": True})
    model = Scripted([NEW])
    svc = service(repo, model)
    task_id = svc.start_task("add more")
    assert idle(svc) and svc.ledger(task_id).data["status"] == "awaiting_approval"
    assert "QUICK MODE" in model.calls[0][1][0]["content"] and not (repo.root / "app/more.py").exists()


def test_quick_mode_with_approval_off_runs_and_verifies_once(repo):
    behavior.apply(repo, {"quick_mode": True, "require_plan_approval": False})
    model = Scripted([edit({"path": "app/more.py", "content": "X = 1\n"}), final("done")])
    svc = service(repo, model)
    task_id = svc.start_task("add more")
    assert idle(svc)
    d = svc.ledger(task_id).data
    assert d["status"] == "completed" and [v["label"] for v in d["verification"]] == ["final"]
    assert "small task" in model.calls[0][1][0]["content"]


def test_a_follow_up_in_a_chat_also_runs_right_away_when_approval_is_off(repo):
    behavior.apply(repo, {"require_plan_approval": False})
    model = Scripted([edit({"path": "app/more.py", "content": "X = 1\n"}), final("done"),
                      edit({"path": "app/more2.py", "content": "Y = 1\n"}), final("done")])
    svc = service(repo, model)
    first = svc.start_task("add more")
    assert idle(svc)
    second = svc.start_task("and more2", chat=first)
    assert idle(svc)
    assert svc.ledger(second).data["status"] == "completed" and svc.ledger(second).data["chat_id"] == first
