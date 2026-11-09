"""Crash/resume: a task left running by a dead process becomes a resumable stopped task; the ledger is made to match the disk; no double runs."""

import json
import os
import subprocess
import sys

import pytest

from ai.dev_agent.engine import recovery, runlock
from ai.dev_agent.engine.loop import AgentError
from ai.dev_agent.ledger.ledger import Ledger
from ai.dev_agent.core import fsutil
from ai.dev_agent.tests.fakes import edit, final, plan
from ai.dev_agent.tests.test_agent_flow import agent

TWO = [{"title": "one", "files": ["app/calc.py"]}, {"title": "two", "files": ["app/new.py"]}]


def dead_pid():
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


def crash(led, pid=None, status="executing"):
    """Simulate a crash: the status stays 'executing' and a lock file of a dead process remains."""
    led.dir.mkdir(parents=True, exist_ok=True)
    (led.dir / "run.lock").write_text(json.dumps({"pid": pid or dead_pid(), "started": 0}))
    led.data["status"] = status
    led.save()


def approved(repo, replies, steps=None):
    a = agent(repo, replies)
    led = a.plan("two parts")
    a.approve(led.id)
    return a, Ledger.load(repo, led.id)


def test_lock_is_taken_and_released_around_a_run(repo):
    a = agent(repo, [plan(files_add=["app/new.py"], files_edit=[], steps=[TWO[1]])])
    led = a.plan("x")
    assert runlock.holder(led) is None and not (led.dir / "run.lock").exists()


def test_a_second_process_cannot_run_the_same_task(repo):
    a = agent(repo, [plan(files_add=["app/new.py"], files_edit=[], steps=[TWO[1]])])
    led = a.plan("x")
    a.approve(led.id)
    holder = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        (led.dir / "run.lock").write_text(json.dumps({"pid": holder.pid, "started": 0}))
        with pytest.raises(AgentError, match="already running"):
            a.execute(led.id)
    finally:
        holder.kill()
        holder.wait()


def test_a_stale_lock_is_taken_over(repo):
    a = agent(repo, [plan(files_add=["app/new.py"], files_edit=[], steps=[TWO[1]]), edit({"path": "app/new.py", "content": "Z = 1\n"}), final("ok")])
    led = a.plan("x")
    a.approve(led.id)
    (led.dir / "run.lock").write_text(json.dumps({"pid": dead_pid(), "started": 0}))
    assert a.execute(led.id).data["status"] == "completed"


def test_a_damaged_lock_file_is_taken_over(repo):
    a = agent(repo, [plan(files_add=["app/new.py"], files_edit=[], steps=[TWO[1]])])
    led = a.plan("x")
    (led.dir / "run.lock").write_text("garbage")
    assert runlock.holder(led) is None
    runlock.acquire(led)
    assert runlock.holder(led) == os.getpid()
    runlock.release(led)


def test_crash_while_executing_becomes_stopped_and_resumable(repo):
    a, led = approved(repo, [plan(files_add=["app/new.py"], files_edit=["app/calc.py"], steps=TWO)])
    led.data["packages"][0]["status"] = "running"
    crash(led)
    reason = recovery.recover_task(Ledger.load(repo, led.id))
    now = Ledger.load(repo, led.id)
    assert reason.startswith("interrupted") and now.data["status"] == "stopped" and "Resume" in now.data["stop_reason"]
    assert now.data["packages"][0]["status"] == "interrupted" and not (now.dir / "run.lock").exists()


def test_crash_while_planning_says_start_again(repo):
    a = agent(repo, [plan(files_add=["app/new.py"])])
    led = a.plan("x")
    led.data.update(status="planning", plan=None, approved_at=None)
    crash(led, status="planning")
    assert "being planned" in recovery.recover_task(Ledger.load(repo, led.id))


def test_a_live_run_is_never_touched(repo):
    a, led = approved(repo, [plan(files_add=["app/new.py"], files_edit=[], steps=[TWO[1]])])
    other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        crash(led, pid=other.pid)
        assert recovery.recover_task(Ledger.load(repo, led.id)) == "" and Ledger.load(repo, led.id).data["status"] == "executing"
    finally:
        other.kill()
        other.wait()


def test_finished_and_stopped_tasks_are_left_alone(repo):
    a = agent(repo, [plan(files_add=["app/new.py"])])
    led = a.plan("x")
    assert recovery.recover(repo) == [] and Ledger.load(repo, led.id).data["status"] == "awaiting_approval"


def test_file_written_just_before_the_crash_is_recovered_into_the_ledger(repo):
    a, led = approved(repo, [plan(files_add=[], files_edit=["app/calc.py"], steps=[TWO[0]])])
    original = (repo.root / "app/calc.py").read_bytes()
    led.snapshot_original("app/calc.py", original)      # the write began: snapshot first, as edit_files does...
    fsutil.atomic_write(repo.root / "app/calc.py", original + b"# half done\n")   # ...then the process died before record_file
    crash(led)
    reason = recovery.recover_task(Ledger.load(repo, led.id))
    entry = Ledger.load(repo, led.id).data["files"]["app/calc.py"]
    assert "app/calc.py: found written on disk but missing in the ledger" in reason and entry["state"] == "written"
    assert entry["sha_now"] == fsutil.sha(original + b"# half done\n")


def test_a_write_that_never_happened_adds_nothing(repo):
    a, led = approved(repo, [plan(files_add=[], files_edit=["app/calc.py"], steps=[TWO[0]])])
    led.snapshot_original("app/calc.py", (repo.root / "app/calc.py").read_bytes())
    crash(led)
    assert "missing in the ledger" not in recovery.recover_task(Ledger.load(repo, led.id))


def test_a_file_edited_by_hand_after_the_last_record_is_flagged(repo):
    a, led = approved(repo, [plan(files_add=[], files_edit=["app/calc.py"], steps=[TWO[0]])])
    led.snapshot_original("app/calc.py", (repo.root / "app/calc.py").read_bytes())
    led.record_file("app/calc.py", "written", "a", "b", "P1", "")
    (repo.root / "app/calc.py").write_text("changed = 1\n")
    crash(led)
    assert "differs from the last recorded write" in recovery.recover_task(Ledger.load(repo, led.id))


def test_resume_after_a_crash_runs_only_the_unfinished_package(repo):
    a = agent(repo, [plan(files_add=["app/new.py"], files_edit=["app/calc.py"], steps=TWO)])
    led = a.plan("two parts")
    a.approve(led.id)
    led = Ledger.load(repo, led.id)
    led.data["packages"] = [{"id": "P1", "title": "one", "steps": ["S1"], "files": ["app/calc.py"], "est_tokens": 1, "status": "done", "summary": "did one", "oversize": False},
                            {"id": "P2", "title": "two", "steps": ["S2"], "files": ["app/new.py"], "est_tokens": 1, "status": "running", "summary": "", "oversize": False}]
    crash(led)
    b = agent(repo, [edit({"path": "app/new.py", "content": "Z = 2\n"}), final("two done")])
    led = b.execute(led.id)
    d = led.data
    assert d["status"] == "completed" and [p["status"] for p in d["packages"]] == ["done", "done"]
    assert "interrupted earlier" in b.provider.calls[0][1][0]["content"] and len(b.provider.calls) == 2     # one package only: finished work is not repeated
