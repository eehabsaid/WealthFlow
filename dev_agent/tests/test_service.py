import time

import pytest

from ..ledger.ledger import Ledger
from ..providers.base import ProviderError
from ..service.events import EventLog
from ..service.tasks import Busy, ServiceError, TaskService
from ..settings.store import Settings
from .fakes import Blocking, Scripted, edit, final, plan, tool


def wait_for(cond, timeout=15.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.03)
    return False


def service(repo, *providers):
    queue = list(providers)
    return TaskService(repo, lambda settings: queue.pop(0) if len(queue) > 1 else queue[0], lambda: Settings(repo).load())


def idle(svc):
    return wait_for(lambda: not svc.state()["busy"])


def types(svc, task_id):
    return [e["type"] for e in svc.log(task_id).after(0)]


def test_full_lifecycle_start_approve_complete_and_events_are_persisted(repo):
    svc = service(repo, Scripted([plan(files_add=["app/more.py"], files_edit=[], steps=[{"title": "add", "files": ["app/more.py"]}]),
                                  edit({"path": "app/more.py", "content": "X = 1\n"}), final("done")]))
    task_id = svc.start_task("add more")
    assert idle(svc) and svc.ledger(task_id).data["status"] == "awaiting_approval"
    svc.approve_plan(task_id)
    assert idle(svc)
    d = svc.ledger(task_id).data
    assert d["status"] == "completed" and d["files"]["app/more.py"]["state"] == "written"
    kinds = types(svc, task_id)
    assert kinds[0] == "phase" and "tool" in kinds and "package" in kinds and "verify" in kinds and kinds[-1] == "done"
    seqs = [e["seq"] for e in svc.log(task_id).after(0)]
    assert seqs == list(range(1, len(seqs) + 1))
    reloaded = EventLog(repo.agent_dir / "tasks" / task_id / "events.jsonl")   # survives a server restart
    assert reloaded.last_seq() == len(seqs)


def test_only_one_run_at_a_time_and_stop_ends_it_promptly(repo):
    model = Blocking([plan()])
    svc = service(repo, model)
    task_id = svc.start_task("t")
    assert idle(svc)
    svc.approve_plan(task_id)                     # execution starts and the model then "thinks" forever
    assert model.started.wait(10)
    with pytest.raises(Busy):
        svc.start_task("another")
    with pytest.raises(Busy):
        svc.approve_plan(task_id)
    began = time.monotonic()
    assert svc.stop() is True
    assert idle(svc) and time.monotonic() - began < 5
    d = svc.ledger(task_id).data
    assert d["status"] == "stopped" and "stopped by user" in d["stop_reason"] and d["packages"][0]["status"] == "stopped"
    assert svc.stop() is False and types(svc, task_id)[-1] == "done"


def test_stop_during_planning(repo):
    model = Blocking()
    svc = service(repo, model)
    task_id = svc.start_task("t")
    assert model.started.wait(10)
    svc.stop()
    assert idle(svc) and svc.ledger(task_id).data["status"] == "stopped" and (repo.agent_dir / "tasks" / task_id / "report.md").is_file()


def test_resume_continues_from_the_ledger_after_stop(repo):
    planner = Scripted([plan(files_add=["app/more.py"], files_edit=[], steps=[{"title": "add", "files": ["app/more.py"]}])])
    first, second = Blocking(), Scripted([edit({"path": "app/more.py", "content": "X = 1\n"}), final("done")])
    svc = service(repo, planner, first, second)   # one model object per run: planning, the first execution, the resume
    task_id = svc.start_task("t")
    assert idle(svc)
    svc.approve_plan(task_id)
    assert first.started.wait(10)
    svc.stop()
    assert idle(svc) and svc.ledger(task_id).data["status"] == "stopped"
    svc.resume(task_id)
    assert idle(svc) and svc.ledger(task_id).data["status"] == "completed" and (repo.root / "app/more.py").exists()


def test_resume_is_refused_when_there_is_nothing_to_resume(repo):
    svc = service(repo, Blocking())
    task_id = svc.start_task("t")
    svc.stop()
    assert idle(svc)
    with pytest.raises(ServiceError):
        svc.resume(task_id)
    with pytest.raises(ServiceError):
        svc.approve_plan(task_id)
    with pytest.raises(ServiceError, match="no readable ledger"):
        svc.ledger("20990101-000000-missing")
    with pytest.raises(ServiceError, match="invalid task id"):
        svc.ledger("missing")


def test_reject_plan(repo):
    svc = service(repo, Scripted([plan()]))
    task_id = svc.start_task("t")
    assert idle(svc)
    svc.reject_plan(task_id)
    assert svc.ledger(task_id).data["status"] == "rejected"
    with pytest.raises(ServiceError):
        svc.approve_plan(task_id)


def test_protected_file_approval_flow_approve_and_deny(repo):
    for answer, expected in ((True, "BALANCE = 2\n"), (False, "BALANCE = 1\n")):
        (repo.root / "app/money.py").write_text("BALANCE = 1\n")
        svc = service(repo, Scripted([plan(files_edit=["app/money.py"], steps=[{"title": "x", "files": ["app/money.py"]}]),
                                      tool("read_file", path="app/money.py"), edit({"path": "app/money.py", "replacements": [{"old": "1", "new": "2"}]}), final("ok")]))
        task_id = svc.start_task("change balance")
        assert idle(svc)
        svc.approve_plan(task_id)
        assert wait_for(lambda: svc.state()["approvals"]), "no approval request appeared"
        pending = svc.state()["approvals"][0]
        assert pending["kind"] == "write" and "PROTECTED" in pending["message"]
        assert svc.answer_approval(pending["id"], answer) is True and svc.answer_approval(pending["id"], True) is False
        assert idle(svc)
        assert (repo.root / "app/money.py").read_text() == expected
        kinds = types(svc, task_id)
        assert "approval_request" in kinds and "approval_result" in kinds
        assert [e for e in svc.log(task_id).after(0) if e["type"] == "approval_result"][0]["approved"] is answer


def test_stop_while_an_approval_is_waiting_denies_it_and_ends_the_run(repo):
    svc = service(repo, Scripted([plan(files_edit=["app/money.py"], steps=[{"title": "x", "files": ["app/money.py"]}]),
                                  edit({"path": "app/money.py", "replacements": [{"old": "1", "new": "2"}]}), final("ok")]))
    task_id = svc.start_task("t")
    assert idle(svc)
    svc.approve_plan(task_id)
    assert wait_for(lambda: svc.state()["approvals"])
    svc.stop()
    assert idle(svc) and (repo.root / "app/money.py").read_text() == "BALANCE = 1\n"
    assert svc.ledger(task_id).data["status"] == "stopped"


def test_provider_problems_are_reported_before_any_task_is_created(repo):
    def broken(settings):
        raise ProviderError("no model chosen")
    svc = TaskService(repo, broken, lambda: Settings(repo).load())
    with pytest.raises(ProviderError):
        svc.start_task("t")
    assert Ledger.list_ids(repo) == []
    with pytest.raises(ServiceError):
        service(repo, Scripted([])).start_task("   ")


def test_an_engine_crash_ends_the_run_visibly(repo):
    class Boom(Scripted):
        def complete(self, system, messages, cancel=None):
            raise RuntimeError("kaboom")
    svc = service(repo, Boom([]))
    task_id = svc.start_task("t")
    assert idle(svc)
    assert svc.ledger(task_id).data["status"] == "stopped" and "kaboom" in svc.ledger(task_id).data["stop_reason"]
    errors = [e for e in svc.log(task_id).after(0) if e["type"] == "error"]
    assert errors and "kaboom" in errors[0]["message"]
