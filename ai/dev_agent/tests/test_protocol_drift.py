"""Real local models drift from the documented JSON shapes; the parser accepts the common drift and the engine keeps the evidence."""

import json

import pytest

from ai.dev_agent.engine.protocol import parse_reply
from ai.dev_agent.engine.session import run_phase
from ai.dev_agent.providers.base import Reply
from ai.dev_agent.engine.cancel import CancelToken
from ai.dev_agent.tools.registry import call as call_tool
from ai.dev_agent.tools.context import ToolContext
from ai.dev_agent.ledger.ledger import Ledger
from ai.dev_agent.tests.fakes import plan
from ai.dev_agent.tests.test_agent_flow import agent, read


@pytest.mark.parametrize("text,kind", [
    ('<think>I should call {"tool": "grep"} maybe</think>\n{"tool": "read_file", "args": {"path": "a.py"}}', "tool"),
    ('<think>unclosed thinking {"final": "x"}', "final"),                                  # JSON only inside the thinking is still found
    ('{"name": "read_file", "arguments": {"path": "a.py"}}', "tool"),
    ('{"name": "read_file", "parameters": "{\\"path\\": \\"a.py\\"}"}', "tool"),
    ('{"tool": "git", "args": "{\\"args\\": [\\"status\\"]}"}', "tool"),
    ('{"summary": "s", "steps": [{"title": "t", "files": []}]}', "plan"),                  # plan without the wrapper
    ('```json\n{"final": "done"}\n```', "final"),
])
def test_drift_shapes_are_accepted(text, kind):
    assert parse_reply(text).kind == kind


@pytest.mark.parametrize("text", ["The file blocks git commands.", "", '{"name": "not_a_tool", "arguments": {}}', "<think>only thinking</think>", '{"x": 1}'])
def test_prose_and_unknown_objects_are_invalid_and_say_what_arrived(text):
    got = parse_reply(text)
    assert got.kind == "invalid" and "reply began" in got.payload


def test_name_and_arguments_values_are_passed_through():
    assert parse_reply('{"name": "read_file", "arguments": {"path": "a.py"}}').payload == ("read_file", {"path": "a.py"})
    assert parse_reply('{"name": "grep", "parameters": "{\\"pattern\\": \\"x\\"}"}').payload == ("grep", {"pattern": "x"})



@pytest.mark.parametrize("text,expected", [
    ('{"tool": "git", "args": "[\\"status\\"]"}', ["status"]),
    ('{"name": "read_file", "arguments": "[\\"app/calc.py\\"]"}', ["app/calc.py"]),
    ('{"name": "grep", "arguments": "\\"pattern\\""}', "pattern"),
])
def test_json_encoded_non_object_arguments_are_preserved_for_registry_validation(text, expected):
    action = parse_reply(text)
    assert action.kind == "tool" and action.payload[1] == expected
    assert call_tool(None, action.payload[0], action.payload[1]) == {"error": "args must be a JSON object"}


def test_empty_path_and_missing_plan_check_files_remain_explicit_errors(repo):
    ctx = ToolContext(project=repo, settings={}, index=None)
    empty_path = parse_reply('{"tool": "read_file", "args": {"path": ""}}')
    assert call_tool(ctx, *empty_path.payload) == {"error": "empty path"}
    missing_files = parse_reply('{"tool": "plan_check", "args": {}}')
    assert call_tool(ctx, *missing_files.payload) == {"error": "give `files`"}


def test_truncated_provider_reply_stops_without_spending_json_retries():
    class Limited:
        calls = 0

        def complete(self, system, messages, cancel=None):
            self.calls += 1
            return Reply('{"tool": "edit_files", "args": {"edits": [', {"output_tokens": 4096}, "length")

    from types import SimpleNamespace

    class Events:
        items = []

        def add_usage(self, usage):
            pass

        def event(self, kind, **data):
            self.items.append((kind, data))

    provider, ledger = Limited(), Events()
    ctx = SimpleNamespace(cancel=CancelToken(), settings={"context_window": 10000, "reserve_tokens": 2000,
                              "max_tool_result_chars": 8000}, ledger=ledger, attachments=None, emit=lambda event: None)
    result = run_phase(ctx, provider, "system", "task", {"final"}, 5, attach=False)
    assert result.kind == "stopped" and "output limit (length)" in result.reason
    assert provider.calls == 1
    assert ledger.items[0][0] == "truncated_reply" and ledger.items[0][1]["text"].startswith('{"tool"')


def test_invalid_replies_are_kept_in_the_ledger_and_a_report_is_written(repo):
    prose = "Sure! guard/commands.py classifies commands as allow, ask or deny."
    a = agent(repo, [read("app/calc.py"), prose, prose, prose])
    led = a.plan("explain")
    ev = [e for e in led.data["events"] if e["kind"] == "invalid_reply"]
    assert led.data["status"] == "stopped" and len(ev) == 3 and ev[0]["text"] == prose
    assert ev[0]["tail"] == prose and ev[0]["chars"] == len(prose)
    assert "The reply began: Sure!" in led.data["stop_reason"] or "reply began: Sure!" in led.data["stop_reason"]
    assert (led.dir / "report.md").is_file()                      # the report exists for a stopped plan too
    nudge = a.provider.calls[2][1][-1]["content"]
    assert '{"final"' in nudge and "EXACTLY ONE JSON" in nudge     # the retry message shows the model the format


def test_a_question_can_be_answered_without_a_plan(repo):
    led = agent(repo, [read("app/calc.py"), json.dumps({"final": "add() returns a + b; nothing needs to change."})]).plan("what does add do?")
    assert led.data["status"] == "answered" and led.data["plan"] is None and led.data["files"] == {}
    text = (led.dir / "report.md").read_text()
    assert "add() returns a + b" in text and "no file changes were made" in text
    assert Ledger.load(repo, led.id).data["answer"].startswith("add()")


def test_plans_still_work_after_the_parser_change(repo):
    assert agent(repo, [plan()]).plan("t").data["status"] == "awaiting_approval"
