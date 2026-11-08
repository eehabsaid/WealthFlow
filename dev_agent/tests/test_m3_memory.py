"""Persistent cross-session memory inside the repo: capture from the ledger, recall within a budget, owner commands, no secrets, no bloat."""

import datetime

import pytest

from ..memory import recall, store
from ..memory.capture import capture
from .test_agent_flow import agent
from .fakes import edit, final, plan


def run_task(repo, goal, replies, approve=True):
    a = agent(repo, replies)
    led = a.plan(goal)
    if approve and led.data["status"] == "awaiting_approval":
        a.approve(led.id)
        led = a.execute(led.id)
    return led


def test_add_entries_are_dated_deduplicated_and_survive_a_new_session(repo):
    assert store.add(repo, "decisions", "use Decimal for money", datetime.date(2026, 11, 1)) == "2026-11-01: use Decimal for money"
    assert store.add(repo, "decisions", "use Decimal for money") == "already recorded"
    assert store.entries(repo, "decisions") == ["2026-11-01: use Decimal for money"]
    assert (repo.agent_dir / "memory" / "decisions.md").is_file()


@pytest.mark.parametrize("text", ["my password is hunter2", "API_KEY=abc", "Bearer xyz", "", "   "])
def test_secrets_and_empty_text_are_refused(repo, text):
    with pytest.raises(store.MemoryRefused):
        store.add(repo, "lessons", text)
    assert store.entries(repo, "lessons") == []


def test_unknown_kind_is_refused(repo):
    with pytest.raises(store.MemoryRefused):
        store.add(repo, "secrets", "x")


def test_files_never_grow_past_the_cap_and_forget_removes_entries(repo):
    for i in range(store.CAP + 20):
        store.add(repo, "lessons", f"lesson number {i}")
    rows = store.entries(repo, "lessons")
    assert len(rows) == store.CAP and rows[-1].endswith(f"{store.CAP + 19}") and (repo.agent_dir / "memory" / "lessons.md").read_text().count("\n") <= 200
    assert store.forget(repo, "lessons", "number 169") == 1 and len(store.entries(repo, "lessons")) == store.CAP - 1


def test_damaged_task_line_is_skipped_not_fatal(repo):
    store.record_task(repo, {"id": "a", "goal": "g", "status": "completed", "date": "2026-11-01"})
    path = repo.agent_dir / "memory" / "tasks.jsonl"
    path.write_text(path.read_text() + "{not json\n", encoding="utf-8")
    assert [t["id"] for t in store.tasks(repo)] == ["a"]


def test_a_task_is_recorded_once_even_when_updated(repo):
    store.record_task(repo, {"id": "a", "goal": "g", "status": "stopped"})
    store.record_task(repo, {"id": "a", "goal": "g", "status": "completed"})
    assert [t["status"] for t in store.tasks(repo)] == ["completed"]


def test_completed_task_is_remembered_with_files_checks_and_structure(repo):
    led = run_task(repo, "add a helper module", [plan(files_add=["app/more.py"], files_edit=[], steps=[{"title": "add", "files": ["app/more.py"]}]),
                                                 edit({"path": "app/more.py", "content": "X = 1\n"}), final("ok")])
    row = [t for t in store.tasks(repo) if t["id"] == led.id][0]
    assert row["status"] == "completed" and row["files"] == ["app/more.py"] and row["checks"].get("tests") == "PASSED"
    assert any("added app/more.py" in e for e in store.entries(repo, "architecture"))


def test_stopped_task_becomes_a_lesson_but_a_user_stop_does_not(repo):
    led = run_task(repo, "do thing", ["blah", "still blah", "nope"], approve=False)
    assert led.data["status"] == "stopped" and any("not valid protocol JSON" in e for e in store.entries(repo, "lessons"))
    led.set_status("stopped", "stopped by user")
    before = store.entries(repo, "lessons")
    capture(led)
    assert store.entries(repo, "lessons") == before


def test_refused_approval_and_rejected_plan_become_decisions(repo):
    led = run_task(repo, "touch the settings", [plan(files_edit=["app/calc.py"]), final("x")], approve=False)
    led.record_approval("write", "k", False, "edit config.json")
    led.set_status("rejected", "plan rejected by the owner")
    capture(led)
    text = " ".join(store.entries(repo, "decisions"))
    assert "owner refused (write): edit config.json" in text and "owner rejected the plan" in text


def test_a_goal_that_contains_a_secret_is_not_stored(repo):
    led = run_task(repo, "use my api_key=SECRET123 to call x", ["blah", "blah", "blah"], approve=False)
    assert "SECRET123" not in (repo.agent_dir / "memory" / "tasks.jsonl").read_text() and led.data["status"] == "stopped"


def test_recall_picks_only_related_entries_within_the_budget(repo):
    store.add(repo, "lessons", "the calc module rounds with banker's rounding")
    store.add(repo, "lessons", "unrelated note about css colours")
    got = recall.pick(repo, "fix rounding in calc module", 2000)
    assert got["lessons"] == [e for e in got["lessons"] if "calc" in e] and len(got["lessons"]) == 1
    assert recall.pick(repo, "zzz qqq", 2000) == {} and recall.pick(repo, "calc rounding", 100) == {}
    assert "## Memory - Lessons" in recall.render(got)


def test_memory_reaches_the_planning_prompt_of_the_next_task(repo):
    store.add(repo, "decisions", "never change the calc module signature")
    a = agent(repo, [final("answer")])
    a.plan("explain the calc module")
    assert "never change the calc module signature" in a.provider.calls[0][1][0]["content"]
