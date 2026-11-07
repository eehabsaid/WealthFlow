"""Event log behaviour, task listing and shutdown of the task service."""

import json
import time

from ..service.events import EventLog
from ..ledger.ledger import Ledger
from .fakes import Blocking, Scripted, plan
from .test_service import idle, service


def test_event_log_wait_wakes_up_and_clips_long_fields(repo):
    import threading
    log = EventLog(repo.agent_dir / "e.jsonl")
    got = {}
    t = threading.Thread(target=lambda: got.update(ev=log.wait(0, 5)))
    t.start()
    time.sleep(0.2)
    log.append({"type": "x", "text": "a" * 5000})
    t.join(5)
    assert got["ev"][0]["seq"] == 1 and len(got["ev"][0]["text"]) < 2100
    assert log.wait(1, 0.1) == []
    log.close()
    assert json.loads((repo.agent_dir / "e.jsonl").read_text().splitlines()[0])["type"] == "x"


def test_list_tasks_newest_first_and_state_when_idle(repo):
    svc = service(repo, Scripted([plan()]))
    assert svc.state() == {"busy": False, "current": None, "approvals": []}
    a = Ledger.create(repo, "first").id
    b = svc.start_task("second")
    assert idle(svc) and [r["id"] for r in svc.list_tasks()][0] == b and a in [r["id"] for r in svc.list_tasks()]


def test_shutdown_stops_a_running_task(repo):
    model = Blocking([plan()])
    svc = service(repo, model)
    task_id = svc.start_task("t")
    assert idle(svc)
    svc.approve_plan(task_id)
    assert model.started.wait(10)
    svc.shutdown(10)
    assert not svc.state()["busy"] and svc.ledger(task_id).data["status"] == "stopped"
