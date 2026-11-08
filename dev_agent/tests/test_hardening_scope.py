"""Hardening 1 and 2: the agent's own coding_agent/ folder is never writable by a task; a work package can only change its own files."""

import json

import pytest

from ..core.project import Project
from ..guard import paths
from ..ledger import plan as planlib
from ..ledger.plan import PlanScope
from ..memory import store
from ..settings.store import Settings
from ..tools import call
from .fakes import Approver, edit, final, plan
from .test_agent_flow import agent, read

INTERNAL = ["coding_agent/config.json", "coding_agent/skills/style.md", "coding_agent/memory/lessons.md", "coding_agent/MEMORY.md",
            "coding_agent/agent_settings.json", "coding_agent/tasks/20261107-000000-x/ledger.json", "Coding_Agent/Config.json"]


def full_plan(**kw):
    return {"files_add": [], "files_edit": [], "files_delete": [], "files_rename": [], **kw}


@pytest.mark.parametrize("rel", INTERNAL)
def test_internal_files_are_denied_even_when_listed_in_the_plan_and_approved(ctx, rel):
    ctx.scope = PlanScope(full_plan(files_add=[rel], files_edit=[rel], files_delete=[rel]))
    ctx.approver = Approver(True)
    for op in ("edit", "create", "delete", "rename"):
        decision = paths.check_write(ctx.project, rel, op, ctx.scope)
        assert decision.action == "deny" and "agent-internal" in decision.reason, (rel, op)


def test_edit_delete_and_rename_tools_refuse_internal_files(repo, ctx):
    target = repo.root / "coding_agent" / "skills" / "style.md"
    target.parent.mkdir(exist_ok=True)
    target.write_text("rules\n", encoding="utf-8")
    ctx.approver = Approver(True)
    ctx.scope = PlanScope(full_plan(files_edit=["coding_agent/skills/style.md", "coding_agent/config.json"], files_add=["coding_agent/x.md"],
                                    files_delete=["coding_agent/skills/style.md"], files_rename=[{"from": "app/old.py", "to": "coding_agent/old.py"}]))
    results = [call(ctx, "edit_files", {"edits": [{"path": "coding_agent/config.json", "replacements": [{"old": "max_file_lines", "new": "max_file_line"}]}]}),
               call(ctx, "edit_files", {"edits": [{"path": "coding_agent/x.md", "content": "hi\n"}]}),
               call(ctx, "delete_file", {"path": "coding_agent/skills/style.md"}),
               call(ctx, "rename_file", {"from": "app/old.py", "to": "coding_agent/old.py"})]
    assert all("agent-internal" in json.dumps(r) for r in results), results
    assert target.read_text() == "rules\n" and (repo.root / "app/old.py").exists() and not (repo.root / "coding_agent/x.md").exists()
    assert '"max_file_lines": 50' in (repo.root / "coding_agent/config.json").read_text()


def test_a_plan_that_lists_an_internal_file_is_rejected_with_the_reason(repo):
    _, problems = planlib.validate(repo, {"summary": "s", "steps": [{"title": "t", "files": []}], "files_edit": ["coding_agent/config.json"]})
    assert problems and "agent-internal" in problems[0]


def test_reading_internal_files_still_works(repo, ctx):
    assert "max_file_lines" in json.dumps(call(ctx, "read_file", {"path": "coding_agent/config.json"}))


def test_the_agents_own_mechanisms_still_write_there(repo):
    assert store.add(repo, "lessons", "kept working").endswith("kept working")
    Settings(repo).set("model", "m1")
    assert (repo.agent_dir / "memory" / "lessons.md").is_file() and Settings(repo).load()["model"] == "m1"


def test_a_differently_named_agent_folder_is_protected_too(tmp_path):
    (tmp_path / "agentdata").mkdir()
    project = Project(tmp_path, "agentdata")
    assert project.internal_reason("agentdata/memory/x.md") and not project.internal_reason("coding_agent/x.md") and not project.internal_reason("src/agentdata.py")


# ---- package scope ---------------------------------------------------------------------------------------------------------------------
PKGS = [{"id": "P1", "files": ["app/calc.py", "app/shared.py"]}, {"id": "P2", "files": ["app/new.py", "app/shared.py"]}]
BIG = full_plan(files_edit=["app/calc.py", "app/shared.py"], files_add=["app/new.py", "app/loose.py"])


def test_scope_by_package_rules():
    p1, p2, final_scope = PlanScope(BIG, PKGS, "P1"), PlanScope(BIG, PKGS, "P2"), PlanScope(BIG, PKGS, "final")
    assert p1.other_package("app/new.py") == "P2" and p2.other_package("app/calc.py") == "P1"
    assert p1.other_package("app/shared.py") == "" and p2.other_package("app/shared.py") == ""     # listed by both: allowed in both
    assert p1.other_package("app/loose.py") == "" and p1.other_package("app/calc.py") == ""          # no package lists it / own file
    assert final_scope.other_package("app/new.py") == "" and PlanScope(BIG).other_package("app/new.py") == ""
    assert PlanScope(BIG, PKGS, "P9").other_package("app/new.py") == ""                              # unknown package id: no restriction invented


def test_guard_denies_another_packages_file_before_any_question(ctx):
    ctx.scope = PlanScope(BIG, PKGS, "P1")
    decision = paths.check_write(ctx.project, "app/new.py", "create", ctx.scope)
    assert decision.action == "deny" and "work package P2" in decision.reason
    assert paths.check_write(ctx.project, "app/calc.py", "edit", ctx.scope).action == "allow"


def test_a_package_cannot_edit_a_file_of_another_package_but_the_task_still_completes(repo):
    steps = [{"title": "calc", "files": ["app/calc.py"]}, {"title": "new", "files": ["app/new.py"]}]
    a = agent(repo, [plan(files_add=["app/new.py"], files_edit=["app/calc.py"], steps=steps)])
    led = a.plan("two parts")
    led.data["packages"] = [{"id": "P1", "title": "calc", "steps": ["S1"], "files": ["app/calc.py"], "est_tokens": 1, "status": "pending", "summary": "", "oversize": False},
                            {"id": "P2", "title": "new", "steps": ["S2"], "files": ["app/new.py"], "est_tokens": 1, "status": "pending", "summary": "", "oversize": False}]
    led.save()
    a.approve(led.id)
    good_calc = edit({"path": "app/calc.py", "replacements": [{"old": "a + b", "new": "a + b + 0"}]})
    b = agent(repo, [read("app/calc.py"), edit({"path": "app/new.py", "content": "Z = 1\n"}), good_calc, final("p1"),
                     edit({"path": "app/new.py", "content": "Z = 2\n"}), final("p2")])
    done = b.execute(led.id)
    transcript = json.dumps(b.provider.calls)
    assert "belongs to work package P2" in transcript and done.data["status"] == "completed"
    assert (repo.root / "app/new.py").read_text() == "Z = 2\n" and done.data["files"]["app/new.py"]["package"] == "P2"
    assert done.data["files"]["app/calc.py"]["package"] == "P1" and [p["status"] for p in done.data["packages"]] == ["done", "done"]
