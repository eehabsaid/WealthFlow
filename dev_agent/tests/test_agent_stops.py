import pytest

from ..engine import report
from ..engine.loop import AgentError
from ..ledger.ledger import Ledger
from .fakes import final, plan, tool, edit
from .test_agent_flow import agent, read


def test_invalid_plan_is_retried_then_gives_up(repo):
    a = agent(repo, [plan(files_edit=[".env"]), plan(files_edit=["../x"]), plan(files_edit=["core/migrations/0001_a.py"])])
    led = a.plan("t")
    assert led.data["status"] == "stopped" and "no valid plan after 3 attempts" in led.data["stop_reason"]


def test_model_that_never_speaks_json_is_stopped(repo):
    led = agent(repo, ["blah", "still blah", "nope"]).plan("t")
    assert led.data["status"] == "stopped" and "not valid protocol JSON" in led.data["stop_reason"]


def test_repeating_the_same_call_is_stopped(repo):
    led = agent(repo, [read("app/calc.py")] * 6).plan("t")
    assert led.data["status"] == "stopped" and "repeated the same call" in led.data["stop_reason"]


def test_step_limit(repo):
    replies = [tool("grep", pattern=f"p{i}") for i in range(10)]
    led = agent(repo, replies, max_steps_per_package=5).plan("t")
    assert "step limit (5)" in led.data["stop_reason"]


def test_provider_failure_stops_cleanly_and_task_can_resume(repo):
    steps = [{"title": "one", "files": ["app/calc.py"]}, {"title": "two", "files": ["app/new.py"]}]
    first = [plan(files_add=["app/new.py"], files_edit=["app/calc.py"], steps=steps)]
    a = agent(repo, first)
    led = a.plan("two parts")
    led = a.approve(led.id)
    led.data["packages"] = [{"id": "P1", "title": "one", "steps": ["S1"], "files": ["app/calc.py"], "est_tokens": 1, "status": "pending", "summary": "", "oversize": False},
                            {"id": "P2", "title": "two", "steps": ["S2"], "files": ["app/new.py"], "est_tokens": 1, "status": "pending", "summary": "", "oversize": False}]
    led.save()
    a.provider.replies = [final("p1 done, nothing to change")]    # P1 finishes, then the model "crashes" on P2
    led = a.execute(led.id)
    assert led.data["packages"][0]["status"] == "done" and led.data["packages"][1]["status"] == "stopped" and led.data["status"] == "stopped"
    b = agent(repo, [edit({"path": "app/new.py", "content": "N = 1\n"}), final("p2 done")])
    led = b.execute(led.id)
    assert led.data["status"] == "completed" and (repo.root / "app/new.py").exists()
    assert len(b.provider.calls) == 2   # P1 was not repeated; each package starts from the ledger brief
    first_msg = b.provider.calls[0][1][0]["content"]
    assert "TASK LEDGER" in first_msg and "[DONE] P1" in first_msg and "CURRENT PACKAGE: P2" in first_msg


def test_a_plan_edited_after_approval_is_refused(repo):
    a = agent(repo, [plan()])
    led = a.plan("t")
    a.approve(led.id)
    led = Ledger.load(repo, led.id)
    led.data["plan"]["files_edit"].append("app/util.py")
    led.save()
    with pytest.raises(AgentError, match="changed after"):
        a.execute(led.id)


def test_large_task_is_split_into_packages_with_ledger_briefs(repo):
    for i in range(24):
        (repo.root / "m").mkdir(exist_ok=True)
        (repo.root / "m" / f"f{i}.py").write_text("x = 1\n" * 3000)
    steps = [{"title": f"edit {i}", "files": [f"m/f{i}.py"]} for i in range(24)]
    a = agent(repo, [plan(files_edit=[f"m/f{i}.py" for i in range(24)], steps=steps)], context_window=60000, reserve_tokens=15000)
    led = a.plan("big refactor")
    pk = led.data["packages"]
    assert len(pk) > 1 and sum(len(p["steps"]) for p in pk) == 24
    brief = led.brief("P2")
    assert "Goal: big refactor" in brief and "CURRENT PACKAGE: P2" in brief and len(brief) <= 6000


def test_report_never_trusts_the_model(repo):
    a = agent(repo, [plan(), final("everything verified and perfect")])
    led = a.plan("t")
    a.approve(led.id)
    a.provider.replies = [final("everything verified and perfect")]
    led = a.execute(led.id)
    text = report.build(led)
    assert "Overall: NOT VERIFIED" in text and "unverified claims" in text and "were not verified by this run" in text


def test_execute_requires_approval_and_status(repo):
    a = agent(repo, [plan()])
    led = a.plan("t")
    with pytest.raises(AgentError):
        a.approve("missing") if False else a.execute(led.id)
    with pytest.raises(FileNotFoundError):
        Ledger.load(repo, "nope")
    assert Ledger.list_ids(repo) == [led.id]


def test_usage_is_tracked_in_the_ledger(repo):
    led = agent(repo, [plan()]).plan("t")
    assert led.data["usage"]["input_tokens"] == 10 and led.data["usage"]["output_tokens"] == 5


def test_noop_or_failed_later_edit_never_hides_an_earlier_write(repo):
    led = Ledger.create(repo, "g")
    led.record_file("a.py", "written", "orig", "v1", "P1")
    led.record_file("a.py", "unchanged", "v1", "v1", "P1", "content already identical")
    led.record_file("a.py", "rolled_back", "v1", "v1", "P1", "x")
    assert led.data["files"]["a.py"]["state"] == "written" and led.data["files"]["a.py"]["sha_before"] == "orig" and led.changed_files() == ["a.py"]
    led.record_file("a.py", "written", "v1", "v2", "P1")
    assert led.data["files"]["a.py"]["sha_before"] == "orig"          # the ORIGINAL content stays the reference
    led.record_file("b.py", "rollback_failed", "x", "y", "P1")
    assert "b.py" in led.changed_files()
