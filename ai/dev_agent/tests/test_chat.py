"""Chats: a follow-up joins the chat of the task it continues, starts with what the earlier tasks did, and waits in a queue while a task runs."""

import threading

import pytest

from ai.dev_agent.engine import chat, recovery
from ai.dev_agent.ledger.ledger import Ledger
from ai.dev_agent.service.tasks import Busy, ServiceError
from ai.dev_agent.tests.fakes import Scripted, edit, final, plan
from ai.dev_agent.tests.test_service import idle, service, wait_for


def test_a_follow_up_joins_the_chat_and_the_planner_sees_the_earlier_task(repo):
    model = Scripted([plan(), plan()])
    svc = service(repo, model)
    first = svc.start_task("add a calculator")
    assert idle(svc)
    second = svc.start_task("now make it faster", chat=first)
    assert idle(svc)
    d1, d2 = svc.ledger(first).data, svc.ledger(second).data
    assert d1["chat_id"] == first and d2["chat_id"] == first and d2["status"] == "awaiting_approval"
    assert "add a calculator" in d2["chat_context"] and "test plan" in d2["chat_context"]
    sent = model.calls[1][1][0]["content"]
    assert sent.startswith("EARLIER IN THIS CHAT") and "add a calculator" in sent and "TASK: now make it faster" in sent
    assert "EARLIER IN THIS CHAT" not in model.calls[0][1][0]["content"]   # a first message has no earlier context
    assert [r["chat"] for r in svc.list_tasks()] == [first, first]


def test_a_follow_up_to_a_follow_up_keeps_the_same_chat(repo):
    svc = service(repo, Scripted([plan(), plan(), plan()]))
    first = svc.start_task("one")
    assert idle(svc)
    second = svc.start_task("two", chat=first)
    assert idle(svc)
    third = svc.start_task("three", chat=second)
    assert idle(svc)
    d = svc.ledger(third).data
    assert d["chat_id"] == first and "one" in d["chat_context"] and "two" in d["chat_context"]


def test_a_new_message_without_chat_is_a_new_chat(repo):
    svc = service(repo, Scripted([plan(), plan()]))
    first = svc.start_task("one")
    assert idle(svc)
    other = svc.start_task("unrelated")
    assert idle(svc)
    d = svc.ledger(other).data
    assert d["chat_id"] == other != first and d["chat_context"] == ""


def test_unknown_chat_is_refused(repo):
    svc = service(repo, Scripted([plan()]))
    with pytest.raises(ServiceError):
        svc.start_task("x", chat="20200101-000000-nothing")


def _running_task(repo, gate):
    """A task that is executing (blocked in the model until `gate` is set); returns the service, the task id, the model."""
    def slow(messages):
        gate.wait(15)
        return edit({"path": "app/more.py", "content": "X = 2\n"})
    add = plan(files_add=["app/more.py"], files_edit=[], steps=[{"title": "add", "files": ["app/more.py"]}])
    model = Scripted([add, slow, final("done"), plan(), plan()])
    svc = service(repo, model)
    first = svc.start_task("first")
    assert idle(svc)
    svc.approve_plan(first)
    assert wait_for(lambda: len(model.calls) >= 2)
    assert svc.state()["busy"]
    return svc, first, model


def test_a_follow_up_sent_while_a_task_runs_is_queued_and_starts_afterwards(repo):
    gate = threading.Event()
    svc, first, model = _running_task(repo, gate)
    second = svc.start_task("second", chat=first)
    assert svc.ledger(second).data["status"] == "queued" and svc.state()["queued"] == [second]
    assert [e["status"] for e in svc.log(second).after(0)] == ["queued"]
    gate.set()
    assert wait_for(lambda: svc.ledger(second).data["status"] == "awaiting_approval")
    assert idle(svc) and svc.state()["queued"] == []
    assert svc.ledger(first).data["status"] == "completed"
    assert "first" in svc.ledger(second).data["chat_context"]


def test_queued_follow_ups_run_in_the_order_they_were_sent(repo):
    gate = threading.Event()
    svc, first, model = _running_task(repo, gate)
    a = svc.start_task("a", chat=first)
    b = svc.start_task("b", chat=first)
    assert svc.state()["queued"] == [a, b]
    gate.set()
    assert wait_for(lambda: svc.ledger(a).data["status"] == "awaiting_approval" and svc.ledger(b).data["status"] == "awaiting_approval")
    assert idle(svc)


def test_a_new_chat_is_still_refused_while_a_task_runs(repo):
    gate = threading.Event()
    svc, first, model = _running_task(repo, gate)
    with pytest.raises(Busy):
        svc.start_task("another topic")
    gate.set()
    assert idle(svc)


def test_stop_also_removes_the_queued_follow_ups(repo):
    gate = threading.Event()
    svc, first, model = _running_task(repo, gate)
    second = svc.start_task("second", chat=first)
    assert svc.stop()
    gate.set()
    assert idle(svc)
    d = svc.ledger(second).data
    assert d["status"] == "stopped" and "removed from the queue" in d["stop_reason"] and svc.state()["queued"] == []
    assert svc.log(second).after(0)[-1]["type"] == "done"


def test_a_queued_task_found_after_a_restart_is_stopped_with_a_clear_reason(repo):
    led = Ledger.create(repo, "waiting", status="queued")
    assert recovery.recover(repo)[0][0] == led.id
    d = Ledger.load(repo, led.id).data
    assert d["status"] == "stopped" and "send it again" in d["stop_reason"]


def test_old_tasks_without_a_chat_id_are_chats_of_one(repo):
    led = Ledger.create(repo, "old")
    del led.data["chat_id"], led.data["chat_context"]
    led.save()
    data = Ledger.load(repo, led.id).data
    assert chat.chat_of(data) == led.id and [d["id"] for d in chat.members(repo, led.id)] == [led.id]


def test_context_keeps_the_newest_tasks_and_stays_short(repo):
    first = Ledger.create(repo, "task 0")
    for n in range(1, 12):
        Ledger.create(repo, f"task {n} " + "x" * 390, first.id)
    text = chat.context(repo, first.id)   # all in the same second: the order still follows creation
    assert len(text) <= chat.MAX_CHARS and "task 11" in text and "task 0" not in text
