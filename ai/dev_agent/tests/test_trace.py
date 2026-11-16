"""Full-trajectory logging: every task's events.jsonl holds the system prompt, the exact messages, the model's own replies and the FULL tool results (redacted),
so complete multi-turn conversations can be rebuilt for training - without changing the live feed the Web UI and the extension read."""

import json
from unittest.mock import patch

from ai.dev_agent import cli
from ai.dev_agent.engine.loop import Agent
from ai.dev_agent.engine.protocol import system_prompt
from ai.dev_agent.service import trajectory
from ai.dev_agent.service.events import EventLog
from ai.dev_agent.settings.store import Settings
from ai.dev_agent.tests.fakes import Approver, Scripted, edit, final, plan, tool

MASK = "***REDACTED***"


def run(repo, replies, question="how does add work?", **settings):
    provider = Scripted(replies)
    agent = Agent(repo, provider, {**Settings(repo).load(), **settings}, Approver(False), events=True)
    ledger = agent.plan(question)
    return agent, ledger, provider, trajectory.read_events(ledger.dir / "events.jsonl")


def only_phase(events):
    found = trajectory.phases(events)
    assert len(found) == 1
    return found[0]


def test_a_question_is_logged_as_one_complete_conversation(repo):
    _, ledger, provider, events = run(repo, [tool("read_file", path="app/calc.py"), tool("grep", pattern="def add"), final("add returns a + b")])
    phase = only_phase(events)
    assert ledger.data["status"] == "answered" and (phase["label"], phase["ended"], phase["steps"], phase["tools"]) == ("plan", "final", 3, ["read_file", "grep"])
    assert phase["system"] == system_prompt(True) and phase["messages"][0]["content"].startswith("TASK: how does add work?")
    assert [m["role"] for m in phase["messages"]] == ["user", "assistant", "user", "assistant", "user", "assistant"]
    assert phase["messages"][-1] == {"role": "assistant", "content": final("add returns a + b")}
    assert phase["clean"] and phase["exact"] and phase["tool_errors"] == 0 and trajectory.alternates(trajectory.conversation(phase))
    assert phase["request"]["provider"] == "scripted" and phase["usage"] == {"input_tokens": 30, "output_tokens": 15}
    assert provider.calls[0][0] == phase["system"]


def test_the_rebuilt_messages_are_exactly_what_the_provider_received_at_every_call(repo):
    _, _, provider, events = run(repo, [tool("read_file", path="app/calc.py"), tool("read_file", path="app/util.py"), final("done")])
    phase = only_phase(events)
    assert len(provider.calls) == 3
    for system, sent in provider.calls:
        assert system == phase["system"] and phase["messages"][: len(sent)] == sent
    assert phase["messages"][1]["content"] == tool("read_file", path="app/calc.py"), "the model's reply is logged exactly as received"
    assert phase["messages"][2]["content"].startswith("TOOL RESULT read_file:\n{")


def test_tool_results_are_logged_in_full_while_the_live_feed_stays_short(repo):
    (repo.root / "app/big.py").write_text("".join(f"value_{i} = {i}\n" for i in range(1, 401)), encoding="utf-8")
    _, ledger, _, events = run(repo, [tool("read_file", path="app/big.py"), final("ok")], max_tool_result_chars=3000)
    logged = next(e for e in events if e.get("kind") == "tool_result")
    assert logged["ok"] and logged["tool"] == "read_file" and logged["args"] == {"path": "app/big.py"}
    assert logged["result"]["end"] == 400 and "value_400 = 400" in logged["result"]["text"] and len(logged["result"]["text"]) > 3000, "the full result"
    assert "chars omitted" in logged["message"] and len(logged["message"]) < 3200 and logged["message"].startswith("TOOL RESULT read_file:\n"), "what the model saw"
    public = next(e for e in events if e.get("type") == "tool")
    assert public["summary"] == f"app/big.py lines 1-400 of {logged['result']['total_lines']}" and "value_400" not in json.dumps(public)


def test_secrets_and_personal_data_are_masked_but_plain_values_survive(repo):
    (repo.root / "app/data.py").write_text('MAIL = "john@example.com"\nPHONE = "+20 100 123 4567"\nPRICE = "$1,200.00"\nPLAIN = 1250.50\nDATE = "2026-11-13"\n'
                                           'TOKEN = "abcd1234efgh5678"\n', encoding="utf-8")
    _, _, _, events = run(repo, [tool("read_file", path="app/data.py"), final("MAIL is john@example.com, PRICE $1,200.00, PLAIN 1250.50")])
    logged = next(e for e in events if e.get("kind") == "tool_result")
    for text in (logged["result"]["text"], logged["message"]):
        assert "john@example.com" not in text and "123 4567" not in text and "1,200.00" not in text and "abcd1234efgh5678" not in text
        assert "1250.50" in text and "2026-11-13" in text and text.count(MASK) == 4
    assert logged["result"]["sha"] and len(logged["result"]["sha"]) == 64, "file hashes are kept"
    reply = next(e for e in events if e.get("kind") == "model" and "PRICE" in e["reply"])
    assert reply["reply"] == '{"final": "MAIL is ***REDACTED***, PRICE ***REDACTED***, PLAIN 1250.50"}' and reply["redactions"] == 2
    assert logged["redactions"] >= 4


def test_trace_events_are_in_the_file_but_never_in_the_live_feed(tmp_path):
    log = EventLog(tmp_path / "events.jsonl")
    log.append({"type": "phase", "phase": "planning"})
    log.append({"type": "trace", "kind": "phase_start", "phase": "plan", "system": "s" * 5000})
    log.append({"type": "context", "used": 5})
    log.append({"type": "trace", "kind": "model", "phase": "plan", "reply": "r" * 5000})
    log.append({"type": "status", "status": "answered"})
    assert [e["seq"] for e in log.after(0)] == [1, 2, 3] and [e["type"] for e in log.after(0)] == ["phase", "context", "status"]
    assert log.last_seq() == 3 and log.after(3) == []
    again = EventLog(tmp_path / "events.jsonl")   # a restart keeps both numberings
    assert [e["seq"] for e in again.after(0)] == [1, 2, 3] and again.append({"type": "trace", "kind": "message"})["tseq"] == 3
    assert again.append({"type": "status", "status": "x"})["seq"] == 4
    lines = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [e["tseq"] for e in lines if "tseq" in e] == [1, 2, 3] and len(next(e for e in lines if e.get("kind") == "phase_start")["system"]) == 5000, "trace text is not clipped"
    assert len(lines) == 7


def test_a_phase_that_needed_a_nudge_or_was_stopped_is_not_clean(repo):
    _, _, _, events = run(repo, ["this is not json", final("ok")])
    phase = only_phase(events)
    assert phase["ended"] == "final" and not phase["clean"] and phase["notes"] == ["invalid_reply_nudge"] and trajectory.alternates(trajectory.conversation(phase))
    _, ledger, _, events = run(repo, ["bad", "worse", "still bad"])
    phase = only_phase(events)
    assert ledger.data["status"] == "stopped" and phase["ended"] == "stopped" and not phase["clean"]
    assert "invalid_reply_nudge" in phase["notes"] and phase["notes"][-1].startswith("stopped: ") and phase["reason"] in phase["notes"][-1]


def test_trimmed_history_marks_the_phase_as_not_exact(repo):
    for name in ("one", "two", "three", "four"):
        (repo.root / f"app/{name}.py").write_text("".join(f"{name}_{i} = {i:05d}  # padding padding\n" for i in range(400)), encoding="utf-8")
    replies = [tool("read_file", path=f"app/{n}.py") for n in ("one", "two", "three", "four")] + [final("ok")]
    _, _, _, events = run(repo, replies, context_window=9000, reserve_tokens=2500, max_steps_per_package=10)
    phase = only_phase(events)
    assert [e["touched"] for e in events if e.get("kind") == "compact"] and phase["ended"] == "final"
    assert not phase["exact"] and not phase["clean"] and "history was trimmed" in phase["notes"]


def test_plan_approve_execute_gives_a_plan_phase_and_a_package_phase(repo):
    helper = "from app.calc import add\n\n\ndef add3(a, b, c):\n    return add(add(a, b), c)\n"
    plan_reply = plan(files_add=["app/more.py"], files_edit=[], steps=[{"title": "add helper", "files": ["app/more.py"]}])
    agent, ledger, _, _ = run(repo, [tool("read_file", path="app/calc.py"), plan_reply, edit({"path": "app/more.py", "content": helper}), final("added a helper")],
                              question="add a helper")
    agent.approve(ledger.id)
    ledger = agent.execute(ledger.id)
    events = trajectory.read_events(ledger.dir / "events.jsonl")
    found = trajectory.phases(events)
    assert ledger.data["status"] == "completed" and [(p["label"], p["ended"], p["clean"]) for p in found] == [("plan", "plan", True), ("package P1", "final", True)]
    assert found[0]["system"] == system_prompt(True) and found[1]["system"] == system_prompt(False)
    assert found[1]["tools"] == ["edit_files"] and found[1]["messages"][2]["content"].startswith("TOOL RESULT edit_files:")
    edit_result = found[1]["results"][0]
    assert edit_result["ok"] and found[1]["tool_errors"] == 0, "a successful edit_files (its `error` key is empty) is not logged as an error"
    assert edit_result["result"]["files"][0]["path"] == "app/more.py" and edit_result["result"]["files"][0]["sha_before"] is None
    assert json.loads(found[0]["messages"][-1]["content"])["plan"]["files_add"] == ["app/more.py"]


def test_a_later_run_of_the_same_task_appends_to_the_same_file_with_continuing_numbers(repo):
    plan_reply = plan(files_add=["app/more.py"], files_edit=[], steps=[{"title": "x", "files": ["app/more.py"]}])
    _, ledger, _, _ = run(repo, [plan_reply], question="add more")
    other = Agent(repo, Scripted([edit({"path": "app/more.py", "content": "X = 1\n"}), final("done")]), Settings(repo).load(), Approver(False), events=True)
    other.approve(ledger.id)
    other.execute(ledger.id)
    events = trajectory.read_events(ledger.dir / "events.jsonl")
    seqs = [e["seq"] for e in events if "seq" in e]
    assert seqs == list(range(1, len(seqs) + 1)) and [e["tseq"] for e in events if "tseq" in e] == list(range(1, len([e for e in events if "tseq" in e]) + 1))
    assert [p["label"] for p in trajectory.phases(events)] == ["plan", "package P1"]


def test_a_torn_or_foreign_line_is_skipped_and_a_missing_file_is_empty(repo, tmp_path):
    _, ledger, _, _ = run(repo, [final("ok")])
    path = ledger.dir / "events.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"type": "trace", "kind": "model", "reply": "cut off')
    assert len(trajectory.phases(trajectory.read_events(path))) == 1 and trajectory.read_events(tmp_path / "none.jsonl") == []
    assert trajectory.phases([{"type": "status"}, {"type": "trace", "kind": "model"}]) == []   # a trace without a start belongs to no phase


def test_the_command_line_agent_writes_events_too(repo):
    with patch.object(cli, "build_provider", return_value=Scripted([final("it adds")])), patch.object(cli, "SecretStore"):
        agent = cli._agent(repo)
        ledger = agent.plan("how does add work?")
    phases = trajectory.phases(trajectory.read_events(ledger.dir / "events.jsonl"))
    assert [(p["label"], p["ended"]) for p in phases] == [("plan", "final")]
