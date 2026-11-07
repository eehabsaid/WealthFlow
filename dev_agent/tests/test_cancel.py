"""Stop must be prompt and total: a model request that is still waiting, a running command, and every child process it started."""

import http.server
import os
import sys
import threading
import time

import pytest

from ..engine.cancel import Cancelled, CancelToken
from ..providers.http import post_json
from ..tools import proctree, runner

SPAWN = ("import subprocess, sys, time, pathlib\n"
         "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
         "pathlib.Path(sys.argv[1]).write_text(str(p.pid))\n"
         "time.sleep(120)\n")


def wait_for(cond, timeout=10.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.05)
    return False


def run_in_thread(argv, cancel=None, timeout=60):
    box = {}
    t = threading.Thread(target=lambda: box.update(res=runner.run(argv, os.getcwd(), timeout, 4000, cancel=cancel)), daemon=True)
    t.start()
    return t, box


def test_token_callbacks_and_reason():
    token, seen = CancelToken(), []
    token.on_cancel(lambda: seen.append("a"))
    remove = token.on_cancel(lambda: seen.append("b"))
    remove()
    token.set("why")
    token.set("again")
    assert seen == ["a"] and token.reason == "why" and token.is_set()
    token.on_cancel(lambda: seen.append("late"))
    assert seen == ["a", "late"]
    with pytest.raises(Cancelled):
        token.check()


def test_a_failing_callback_does_not_stop_the_others():
    token, seen = CancelToken(), []
    token.on_cancel(lambda: 1 / 0)
    token.on_cancel(lambda: seen.append("ok"))
    token.set()
    assert seen == ["ok"]


def test_command_stop_kills_the_whole_tree(tmp_path):
    pidfile, cancel = tmp_path / "pid", CancelToken()
    t, box = run_in_thread(["python", "-c", SPAWN, str(pidfile)], cancel)
    assert wait_for(pidfile.exists)
    grandchild = int(pidfile.read_text())
    assert proctree.pid_alive(grandchild)
    started = time.monotonic()
    cancel.set()
    t.join(15)
    assert not t.is_alive() and box["res"]["status"] == "CANCELLED" and time.monotonic() - started < 10
    assert wait_for(lambda: not proctree.pid_alive(grandchild)), "a grandchild survived Stop"


def test_timeout_kills_the_whole_tree(tmp_path):
    pidfile = tmp_path / "pid"
    res = runner.run(["python", "-c", SPAWN, str(pidfile)], os.getcwd(), 1, 4000)
    assert res["timed_out"] and res["status"] == "FAILED"
    assert wait_for(lambda: not proctree.pid_alive(int(pidfile.read_text())))


def test_background_leftovers_of_a_finished_command_are_removed(tmp_path):
    pidfile = tmp_path / "pid"
    code = ("import subprocess, sys, pathlib\n"
            "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
            "pathlib.Path(sys.argv[1]).write_text(str(p.pid))\n")
    res = runner.run(["python", "-c", code, str(pidfile)], os.getcwd(), 30, 4000)
    assert res["status"] == "PASSED"
    assert wait_for(lambda: not proctree.pid_alive(int(pidfile.read_text()))), "a leftover background process was not cleaned up"


def test_cancel_before_start_runs_nothing(tmp_path):
    cancel = CancelToken()
    cancel.set()
    res = runner.run(["python", "-c", f"open(r'{tmp_path / 'x'}', 'w')"], os.getcwd(), 30, cancel=cancel)
    assert res["status"] == "CANCELLED" and not (tmp_path / "x").exists()


def test_kill_all_stops_everything_that_runs(tmp_path):
    pidfile = tmp_path / "pid"
    t, box = run_in_thread(["python", "-c", SPAWN, str(pidfile)])
    assert wait_for(pidfile.exists)
    assert proctree.kill_all() >= 1
    t.join(15)
    assert not t.is_alive() and wait_for(lambda: not proctree.pid_alive(int(pidfile.read_text())))


def test_pid_alive_is_accurate_for_a_finished_process():
    import subprocess
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    assert proctree.pid_alive(os.getpid()) and not proctree.pid_alive(p.pid)


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Objects")
def test_windows_stop_kills_cmd_python_grandchildren(tmp_path):
    """RUN THIS ON WINDOWS: cmd -> python -> python must all be gone after Stop."""
    pidfile, cancel, script = tmp_path / "pid", CancelToken(), tmp_path / "spawn.py"
    script.write_text(SPAWN, encoding="utf-8")   # cmd.exe cuts a command line at the first newline, so the script must be a file
    t, box = run_in_thread(["cmd", "/c", sys.executable, str(script), str(pidfile)], cancel)
    assert wait_for(pidfile.exists, 20)
    grandchild = int(pidfile.read_text())
    cancel.set()
    t.join(20)
    assert box["res"]["status"] == "CANCELLED" and not box["res"].get("orphans_possible")
    assert wait_for(lambda: not proctree.pid_alive(grandchild)), "a Windows grandchild survived Stop"


class Hang(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        time.sleep(30)

    def log_message(self, *a):
        pass


def test_stop_cuts_off_a_model_request_that_is_still_generating():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Hang)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    cancel, box = CancelToken(), {}

    def call():
        try:
            post_json(f"http://127.0.0.1:{srv.server_port}/x", {}, {"a": 1}, 60, cancel=cancel)
        except Cancelled:
            box["cancelled"] = time.monotonic()

    t = threading.Thread(target=call, daemon=True)
    t.start()
    time.sleep(0.5)
    began = time.monotonic()
    cancel.set()
    t.join(10)
    srv.shutdown()
    assert not t.is_alive() and "cancelled" in box and box["cancelled"] - began < 5


def test_cancel_before_a_request_raises_at_once():
    cancel = CancelToken()
    cancel.set()
    with pytest.raises(Cancelled):
        post_json("http://127.0.0.1:1/x", {}, {}, 5, cancel=cancel)


@pytest.mark.skipif(os.name == "nt", reason="zombie processes exist on POSIX only")
def test_pid_alive_treats_a_finished_but_uncollected_process_as_gone():
    import subprocess
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    try:
        assert wait_for(lambda: not proctree.pid_alive(p.pid), 10)
    finally:
        p.wait()
