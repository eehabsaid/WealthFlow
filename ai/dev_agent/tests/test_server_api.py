import json
import threading
import time
import urllib.request

import pytest

from ai.dev_agent.tests.apihelp import TOKEN, Api
from ai.dev_agent.tests.fakes import Blocking, Scripted, edit, final, plan, tool


@pytest.fixture
def make(repo):
    made = []

    def build(*providers):
        made.append(Api(repo, *providers))
        return made[-1]
    yield build
    for a in made:
        a.close()


def wait(cond, timeout=15):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.05)
    return False


def test_full_flow_over_http_with_diff_files_and_report(make, repo):
    api = make(Scripted([plan(files_add=["app/more.py"], files_edit=["app/calc.py"], steps=[{"title": "go", "files": ["app/more.py", "app/calc.py"]}]),
                         edit({"path": "app/more.py", "content": "X = 1\n"}), final("done")]))
    status, body = api.json("POST", "/api/tasks", {"goal": "add more"})
    assert status == 202
    task_id = body["id"]
    assert api.wait_idle()
    assert api.json("GET", f"/api/tasks/{task_id}")[1]["status"] == "awaiting_approval"
    assert api.json("GET", "/api/tasks")[1]["tasks"][0]["id"] == task_id
    assert api.json("POST", f"/api/tasks/{task_id}/approve")[0] == 200
    assert api.wait_idle()
    task = api.json("GET", f"/api/tasks/{task_id}")[1]
    assert task["status"] == "completed" and "events" not in task
    files = api.json("GET", f"/api/tasks/{task_id}/files")[1]["files"]
    assert [f["path"] for f in files] == ["app/more.py"] and files[0]["state"] == "written"
    d = api.json("GET", f"/api/tasks/{task_id}/diff?path=app/more.py")[1]
    assert "+X = 1" in json.dumps(d)
    assert api.call("GET", f"/api/tasks/{task_id}/file?path=app/more.py&version=current")[1] == b"X = 1\n"
    assert api.json("GET", f"/api/tasks/{task_id}/file?path=app/more.py&version=original")[0] == 404   # did not exist before
    status, text, head = api.call("GET", f"/api/tasks/{task_id}/report")
    assert status == 200 and b"Status: COMPLETED" in text and head["Content-Type"].startswith("text/markdown")


def test_file_and_diff_endpoints_only_serve_files_of_the_task(make, repo):
    api = make(Scripted([plan(files_add=["app/more.py"], files_edit=[], steps=[{"title": "go", "files": ["app/more.py"]}]),
                         edit({"path": "app/more.py", "content": "X = 1\n"}), final("done")]))
    task_id = api.json("POST", "/api/tasks", {"goal": "t"})[1]["id"]
    api.wait_idle()
    api.json("POST", f"/api/tasks/{task_id}/approve")
    api.wait_idle()
    (repo.root / ".env").write_text("SECRET=1\n")
    for path in ("app/calc.py", ".env", "../outside", "coding_agent/config.json", "C:/Windows/win.ini", "/etc/passwd", "app/../.env"):
        for ep in ("file", "diff"):
            status, body, _ = api.call("GET", f"/api/tasks/{task_id}/{ep}?path={path}")
            assert status in (400, 404) and b"SECRET" not in body, (ep, path, status)


def test_events_catch_up_long_poll_and_sse_with_resume(make):
    api = make(Scripted([plan()]))
    task_id = api.json("POST", "/api/tasks", {"goal": "t"})[1]["id"]
    api.wait_idle()
    first = api.json("GET", f"/api/tasks/{task_id}/events")[1]
    seqs = [e["seq"] for e in first["events"]]
    assert seqs == list(range(1, len(seqs) + 1)) and first["next"] == seqs[-1]
    assert api.json("GET", f"/api/tasks/{task_id}/events?after={first['next']}")[1]["events"] == []
    started = time.monotonic()
    assert api.json("GET", f"/api/tasks/{task_id}/events?after={first['next']}&wait=1")[1]["events"] == []
    assert time.monotonic() - started >= 0.8
    req = urllib.request.Request(f"http://127.0.0.1:{api.port}/api/tasks/{task_id}/events?stream=1", headers={"Authorization": f"Bearer {TOKEN}", "Last-Event-ID": "1"})
    with urllib.request.urlopen(req, timeout=10) as r:
        assert r.headers["Content-Type"].startswith("text/event-stream")
        lines = []
        while len(lines) < 200:
            lines.append(r.readline().decode())
            if lines[-1].startswith("id: ") and int(lines[-1][4:]) == seqs[-1]:
                break
    ids = [int(x[4:]) for x in lines if x.startswith("id: ")]
    assert ids == seqs[1:], "resume must continue after Last-Event-ID without repeating"


def test_sse_delivers_new_events_live(make):
    api = make(Scripted([plan(), final("x")]))
    task_id = api.json("POST", "/api/tasks", {"goal": "t"})[1]["id"]
    api.wait_idle()
    got = []

    def read():
        req = urllib.request.Request(f"http://127.0.0.1:{api.port}/api/tasks/{task_id}/events?stream=1", headers={"Authorization": f"Bearer {TOKEN}"})
        with urllib.request.urlopen(req, timeout=15) as r:
            for raw in r:
                if raw.startswith(b"event: "):
                    got.append(raw[7:].strip().decode())
                    if got.count("done") == 2:   # the plan phase ends with one "done", the executed task with a second
                        return
    t = threading.Thread(target=read, daemon=True)
    t.start()
    time.sleep(0.3)
    api.json("POST", f"/api/tasks/{task_id}/approve")
    t.join(15)
    assert "package" in got and got.count("done") == 2


def test_approval_over_http(make, repo):
    (repo.root / "app/money.py").write_text("BALANCE = 1\n")
    api = make(Scripted([plan(files_edit=["app/money.py"], steps=[{"title": "x", "files": ["app/money.py"]}]), tool("read_file", path="app/money.py"),
                         edit({"path": "app/money.py", "replacements": [{"old": "1", "new": "2"}]}), final("ok")]))
    task_id = api.json("POST", "/api/tasks", {"goal": "t"})[1]["id"]
    api.wait_idle()
    api.json("POST", f"/api/tasks/{task_id}/approve")
    assert wait(lambda: api.json("GET", "/api/approvals")[1]["approvals"])
    pending = api.json("GET", "/api/approvals")[1]["approvals"][0]
    assert api.json("POST", "/api/approvals/a999", {"approve": True})[0] == 404
    assert api.json("POST", f"/api/approvals/{pending['id']}", {"approve": "yes"})[0] == 400
    assert api.json("POST", f"/api/approvals/{pending['id']}", {"approve": False})[0] == 200
    assert api.json("POST", f"/api/approvals/{pending['id']}", {"approve": True})[0] == 404   # first answer won
    assert api.wait_idle() and (repo.root / "app/money.py").read_text() == "BALANCE = 1\n"


def test_stop_over_http_kills_the_running_command(make, repo):
    marker = repo.root / "tests" / "test_slow.py"
    marker.write_text("import time\n\ndef test_slow():\n    time.sleep(120)\n")
    api = make(Scripted([plan(), tool("run_command", command="python -m pytest -q -p no:cacheprovider tests/test_slow.py", reason="x"), final("never")]))
    task_id = api.json("POST", "/api/tasks", {"goal": "t"})[1]["id"]
    api.wait_idle()
    api.json("POST", f"/api/tasks/{task_id}/approve")
    assert wait(lambda: api.json("GET", "/api/state")[1]["busy"])
    time.sleep(1.5)   # let pytest actually start
    started = time.monotonic()
    assert api.json("POST", "/api/stop")[1] == {"stopped": True}
    assert api.wait_idle(15) and time.monotonic() - started < 12
    d = api.json("GET", f"/api/tasks/{task_id}")[1]
    assert d["status"] == "stopped" and "stopped by user" in d["stop_reason"]
    assert api.json("POST", "/api/stop")[1] == {"stopped": False}


def test_busy_and_unknown_task_errors(make):
    model = Blocking([plan()])
    api = make(model)
    task_id = api.json("POST", "/api/tasks", {"goal": "t"})[1]["id"]
    api.wait_idle()
    api.json("POST", f"/api/tasks/{task_id}/approve")
    assert model.started.wait(10)
    assert api.json("POST", "/api/tasks", {"goal": "second"})[0] == 409
    api.json("POST", "/api/stop")
    api.wait_idle()
    assert api.json("GET", "/api/tasks/20990101-000000-nothing")[0] == 404
    assert api.json("POST", "/api/tasks", {"goal": ""})[0] == 400
    assert api.json("POST", "/api/tasks", {})[0] == 400


def test_shutdown_endpoint_stops_the_server(make):
    api = make(Scripted([plan()]))
    assert api.json("POST", "/api/shutdown")[0] == 200
    assert api.server.stopping.wait(5)
    api.thread.join(5)
    assert not api.thread.is_alive()
