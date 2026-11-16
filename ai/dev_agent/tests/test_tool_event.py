"""The live feed's `tool` events (Web UI, VS Code extension): `ok` and the one-line summary follow what the tool really said. edit_files always carries an `error` key
(empty when all went well), so having the key must never mean "failed" - the feed used to show every successful edit as failed, with a blank summary."""

import pytest

from ai.dev_agent.engine.loop import Agent
from ai.dev_agent.engine.session import _summary
from ai.dev_agent.engine.trace import succeeded
from ai.dev_agent.service import trajectory
from ai.dev_agent.settings.store import Settings
from ai.dev_agent.tests.fakes import Approver, Scripted, edit, final, plan, tool

WRITTEN = {"ok": True, "error": "", "files": [{"path": "app/more.py", "state": "written"}, {"path": "app/calc.py", "state": "unchanged"}]}
REJECTED = {"ok": False, "error": "rejected: nothing was written (all-or-nothing)", "files": [{"path": "app/more.py", "state": "rejected"}]}


@pytest.mark.parametrize("result,expected", [(WRITTEN, True), (REJECTED, False), ({"ok": False, "error": ""}, False), ({"error": "no such file"}, False),
                                             ({"error": ""}, True), ({"path": "a.py", "text": "x"}, True), ({"ok": True}, True)])
def test_one_rule_for_success_the_tool_says_ok_else_it_has_no_error_text(result, expected):
    assert succeeded(result) is expected


def test_the_summary_of_a_successful_edit_lists_the_files_and_an_error_text_is_shown_as_it_is():
    assert _summary("edit_files", WRITTEN) == "app/more.py: written, app/calc.py: unchanged"
    assert _summary("edit_files", REJECTED) == "rejected: nothing was written (all-or-nothing)"
    assert _summary("read_file", {"error": "no such file: app/x.py"}) == "no such file: app/x.py"
    assert _summary("read_file", {"error": "", "path": "a.py", "start": 1, "end": 3, "total_lines": 3}) == "a.py lines 1-3 of 3"


def test_the_live_feed_shows_a_successful_edit_as_ok_and_a_failed_read_as_not_ok(repo):
    helper = "def more():\n    return 1\n"
    steps = [{"title": "add", "files": ["app/more.py"]}]
    replies = [tool("read_file", path="app/missing.py"), plan(files_add=["app/more.py"], files_edit=[], steps=steps), edit({"path": "app/more.py", "content": helper}), final("added")]
    agent = Agent(repo, Scripted(replies), Settings(repo).load(), Approver(False), events=True)
    ledger = agent.plan("add a helper")
    agent.approve(ledger.id)
    ledger = agent.execute(ledger.id)
    shown = [e for e in trajectory.read_events(ledger.dir / "events.jsonl") if e.get("type") == "tool"]
    assert [(e["name"], e["ok"]) for e in shown] == [("read_file", False), ("edit_files", True)]
    assert "missing.py" in shown[0]["summary"] and shown[1]["summary"] == "app/more.py: written"
