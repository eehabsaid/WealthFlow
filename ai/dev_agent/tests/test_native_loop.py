"""The Hermes-style loop: native tool calls, results back as tool messages, malformed output fed back, text fallback, direct mode, verification."""

import json

from ai.dev_agent.engine.loop import Agent
from ai.dev_agent.providers.base import MalformedOutput, NoToolSupport
from ai.dev_agent.settings.store import Settings
from ai.dev_agent.tests.fakes import Approver, Scripted, final, tool
from ai.dev_agent.tests.native_fakes import Native, call, say


def direct_agent(repo, provider, approver=None, **settings):
    s = {**Settings(repo).load(), "require_plan_approval": False, **settings}
    return Agent(repo, provider, s, approver or Approver(False))


def test_native_tool_calls_run_and_results_go_back_as_tool_messages(repo):
    model = Native([call(("read_file", {"path": "app/calc.py"})), call(("edit_file", {"path": "app/calc.py", "old": "a + b", "new": "a + b + 0"})), say("changed add")])
    led = direct_agent(repo, model).start("change add to add zero")
    assert led.data["status"] == "completed" and "a + b + 0" in (repo.root / "app/calc.py").read_text()
    second = model.calls[1]["messages"]
    assert second[1]["role"] == "assistant" and second[1]["tool_calls"][0]["name"] == "read_file"
    assert second[2]["role"] == "tool" and second[2]["tool_call_id"] == "c1" and "def add" in second[2]["content"]
    names = {t["name"] for t in model.calls[0]["tools"]}
    assert {"shell", "read_file", "write_file", "edit_file", "grep", "glob", "list_dir", "web_search", "web_fetch", "todo", "subagent"} <= names
    assert "submit_plan" not in names and "JSON object per message" not in model.calls[0]["system"]   # tools travel natively, not in the prompt


def test_several_tool_calls_in_one_reply_each_get_a_result(repo):
    model = Native([call(("list_dir", {}), ("glob", {"pattern": "**/*.py"})), say("looked")])
    led = direct_agent(repo, model).start("what files are there?")
    tools = [m for m in model.calls[1]["messages"] if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tools] == ["c1", "c2"] and led.data["status"] == "answered" and led.data["answer"] == "looked"


def test_plain_prose_from_a_native_model_is_its_answer(repo):
    led = direct_agent(repo, Native([say("add() sums two numbers; see app/calc.py")])).start("what does add do?")
    assert led.data["status"] == "answered" and "sums two numbers" in led.data["answer"]


def test_a_broken_tool_call_written_as_text_is_fed_back_not_fatal(repo):
    model = Native([say('{"tool": "read_file", "args": {"path": '), call(("read_file", {"path": "app/calc.py"})), say("it adds")])
    led = direct_agent(repo, model).start("explain add")
    assert led.data["status"] == "answered"
    assert "could not be used" in model.calls[1]["messages"][-1]["content"]


def test_a_json_call_in_the_text_still_works_with_a_native_provider(repo):
    model = Native([say(tool("read_file", path="app/calc.py")), say("done reading")])
    led = direct_agent(repo, model).start("explain add")
    assert led.data["status"] == "answered" and model.calls[1]["messages"][2]["role"] == "tool"


def test_server_side_decode_error_is_fed_back_and_the_run_goes_on(repo):
    model = Native([MalformedOutput("your last tool call could not be parsed"), call(("read_file", {"path": "app/calc.py"})), say("ok")])
    led = direct_agent(repo, model).start("explain add")
    assert led.data["status"] == "answered" and "could not be parsed" in model.calls[1]["messages"][-1]["content"]


def test_too_many_undecodable_replies_in_a_row_stop_with_the_reason(repo):
    led = direct_agent(repo, Native([MalformedOutput("bad")] * 6)).start("explain add")
    assert led.data["status"] == "stopped" and "5 times in a row" in led.data["stop_reason"]


def test_a_server_without_tools_api_switches_to_the_text_protocol(repo):
    model = Native([NoToolSupport("registry.ollama.ai/x does not support tools"), say(tool("read_file", path="app/calc.py")), say(json.dumps({"final": "adds"}))])
    led = direct_agent(repo, model).start("explain add")
    assert led.data["status"] == "answered" and model.native_tools is False
    assert "JSON object per message" in model.calls[1]["system"] and model.calls[1]["tools"] is None


def test_arguments_of_the_wrong_type_are_fitted_and_missing_ones_named(repo):
    model = Native([call(("read_file", {"path": "app/calc.py", "start": "1", "end": "2"}), ("edit_file", {"path": "app/calc.py"})), say("ok")])
    direct_agent(repo, model).start("explain add")
    results = [m["content"] for m in model.calls[1]["messages"] if m["role"] == "tool"]
    assert '"start": 1' in results[0] and "missing required argument(s): old, new" in results[1]


def test_a_change_task_answered_with_words_is_sent_back_then_stopped(repo):
    led = direct_agent(repo, Native([say("done, I changed it")] * 4)).start("add a docstring to app/calc.py")
    assert led.data["status"] == "stopped" and "without changing any file" in led.data["stop_reason"]


def test_failed_checks_go_back_into_the_same_conversation(repo):
    broken = "import os\n\n\ndef f():\n    return 1\n"
    model = Native([call(("write_file", {"path": "app/f.py", "content": broken})), say("added f"),
                    call(("write_file", {"path": "app/f.py", "content": "def f():\n    return 1\n", "overwrite": True})), say("removed the import")])
    led = direct_agent(repo, model).start("add app/f.py with f()")
    assert led.data["status"] == "completed"
    followup = model.calls[2]["messages"]
    assert followup[0]["content"].startswith("TASK") and any("CHECK FAILED: pyflakes" in m["content"] for m in followup if m["role"] == "user")
    assert any(m["role"] == "tool" for m in followup)   # it still has everything it did before


def test_plan_approval_on_planning_phase_uses_submit_plan(repo):
    plan = {"summary": "s", "steps": [{"title": "t", "files": ["app/calc.py"]}], "files_edit": ["app/calc.py"]}
    model = Native([call(("read_file", {"path": "app/calc.py"})), call(("submit_plan", plan))])
    agent = Agent(repo, model, Settings(repo).load(), Approver(False))
    led = agent.start("change add")
    assert led.data["status"] == "awaiting_approval" and led.data["plan"]["files_edit"] == ["app/calc.py"]
    names = {t["name"] for t in model.calls[0]["tools"]}
    assert "submit_plan" in names and "shell" not in names and "edit_file" not in names   # planning is read-only


def test_text_protocol_models_still_run_the_same_loop(repo):
    model = Scripted([tool("read_file", path="app/calc.py"), final("it adds")])
    led = direct_agent(repo, model).start("explain add")
    assert led.data["status"] == "answered"
