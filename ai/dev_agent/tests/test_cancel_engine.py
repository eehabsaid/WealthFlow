"""Stop/Cancel inside the engine loop (the model request and the tool calls)."""

import threading

from ai.dev_agent.engine.session import run_phase
from ai.dev_agent.tools import proctree
from ai.dev_agent.tests.fakes import Blocking, Scripted, tool
from ai.dev_agent.tests.test_cancel import SPAWN, wait_for


def test_run_phase_does_not_call_the_model_when_already_stopped(ctx):
    ctx.cancel.set()
    model = Scripted([tool("grep", pattern="x")])
    res = run_phase(ctx, model, "sys", "go", {"final"}, 10)
    assert res.kind == "stopped" and res.reason == "stopped by user" and model.calls == []


def test_run_phase_stops_a_model_that_is_still_thinking(ctx):
    model = Blocking()
    box = {}
    t = threading.Thread(target=lambda: box.update(res=run_phase(ctx, model, "sys", "go", {"final"}, 10)), daemon=True)
    t.start()
    assert model.started.wait(5)
    ctx.cancel.set()
    t.join(10)
    assert not t.is_alive() and box["res"].kind == "stopped" and box["res"].reason == "stopped by user"


def test_run_phase_stops_between_steps(ctx):
    def stop_then_call(messages):
        ctx.cancel.set()
        return tool("grep", pattern="def")
    model = Scripted([stop_then_call, tool("grep", pattern="never")])
    res = run_phase(ctx, model, "sys", "go", {"final"}, 10)
    assert res.kind == "stopped" and len(model.calls) == 1


def test_a_stopped_command_tool_reports_cancelled_and_the_run_ends(ctx, tmp_path):
    ctx.approver = type("A", (), {"ask": lambda self, k, m: True})()
    pidfile = tmp_path / "pid"
    code = SPAWN.replace("\n", "; ").replace("; ;", ";")
    model = Scripted([tool("run_command", command=f'python -c "{SPAWN_ONE}" {pidfile}', reason="x"), tool("grep", pattern="never")])
    box = {}
    t = threading.Thread(target=lambda: box.update(res=run_phase(ctx, model, "sys", "go", {"final"}, 10)), daemon=True)
    t.start()
    assert wait_for(pidfile.exists, 15) and code
    ctx.cancel.set()
    t.join(15)
    assert not t.is_alive() and box["res"].kind == "stopped" and wait_for(lambda: not proctree.pid_alive(int(pidfile.read_text())))


SPAWN_ONE = ("import subprocess,sys,time,pathlib;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(120)']);"
             "pathlib.Path(sys.argv[1]).write_text(str(p.pid));time.sleep(120)")
