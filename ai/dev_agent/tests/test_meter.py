"""The context meter: the pure reading (levels, provider numbers vs the agent's own estimate) and the `context` events the engine emits after every model call."""

import pytest

from ai.dev_agent.engine import meter
from ai.dev_agent.engine.budget import Budget, tokens
from ai.dev_agent.engine.loop import Agent
from ai.dev_agent.providers.base import Provider, Reply
from ai.dev_agent.settings.store import Settings
from ai.dev_agent.tests.fakes import Approver, Scripted, final, tool


def read_at(used, window=100_000, reserve=20_000):
    return meter.snapshot(used - 5, 5, used, window, reserve)


def test_levels_follow_the_usable_limit_not_the_window():
    assert [read_at(u)["level"] for u in (0, 63_999, 64_000, 75_999, 76_000, 80_000, 99_999)] == ["ok", "ok", "warn", "warn", "critical", "critical", "critical"]


def test_the_numbers_for_a_normal_reading():
    snap = meter.snapshot(40_000, 2_000, 42_500, 150_000, 28_000)
    assert (snap["used"], snap["window"], snap["reserve"], snap["limit"]) == (42_000, 150_000, 28_000, 122_000)
    assert (snap["percent"], snap["remaining"], snap["remaining_usable"], snap["level"], snap["source"]) == (28.0, 108_000, 80_000, "ok", "provider")
    assert snap["reported"] == {"input_tokens": 40_000, "output_tokens": 2_000} and snap["estimate"] == 42_500


def test_over_the_window_never_gives_negative_remaining():
    snap = read_at(160_000, 150_000, 28_000)
    assert (snap["remaining"], snap["remaining_usable"], snap["level"], snap["percent"]) == (0, 0, "critical", 106.7)


def test_a_provider_count_that_looks_complete_is_used_as_reported():
    snap = meter.snapshot(9_000, 500, 9_300, 50_000, 10_000)
    assert (snap["used"], snap["source"]) == (9_500, "provider")


def test_a_cache_reduced_prompt_count_falls_back_to_the_estimate_and_keeps_both_numbers():
    """Ollama reports only the newly evaluated tokens when its prompt cache is reused: 500 reported vs ~20,000 really in the conversation."""
    snap = meter.snapshot(300, 200, 20_000, 50_000, 10_000)
    assert (snap["used"], snap["source"], snap["reported"], snap["estimate"]) == (20_000, "estimate", {"input_tokens": 300, "output_tokens": 200}, 20_000)


@pytest.mark.parametrize("usage", [(0, 0), (None, None), ("", "7"), (-5, -5)])
def test_missing_or_garbage_usage_uses_the_estimate(usage):
    snap = meter.snapshot(usage[0], usage[1], 1234, 50_000, 10_000)
    assert snap["source"] == "estimate" and snap["used"] == 1234


def test_a_window_that_is_all_reserve_does_not_divide_by_zero():
    snap = meter.snapshot(10, 5, 15, 1000, 1000)
    assert snap["limit"] == 1 and snap["level"] == "critical"


class Usage(Provider):
    """Replies from a list with the given (input_tokens, output_tokens) per call."""
    name = "usage"

    def __init__(self, replies, usages):
        super().__init__("fake", "http://localhost")
        self.replies, self.usages, self.calls = list(replies), list(usages), []

    def complete(self, system, messages, cancel=None):
        self.calls.append((system, [dict(m) for m in messages]))
        usage = self.usages.pop(0)
        return Reply(self.replies.pop(0), {"input_tokens": usage[0], "output_tokens": usage[1]})


def run_question(repo, provider, **settings):
    events = []
    agent = Agent(repo, provider, {**Settings(repo).load(), **settings}, Approver(False), events.append)
    ledger = agent.plan("how does add work?")
    return ledger, [e for e in events if e.get("type") == "context"], events


def test_every_model_call_gets_a_context_event_with_the_reported_usage(repo):
    provider = Usage([tool("read_file", path="app/calc.py"), final("it adds")], [(1_000, 40), (1_600, 20)])
    ledger, ctx_events, _ = run_question(repo, provider, context_window=50_000, reserve_tokens=10_000)
    assert ledger.data["status"] == "answered" and len(ctx_events) == len(provider.calls) == 2
    assert [(e["step"], e["phase"], e["used"], e["source"]) for e in ctx_events] == [(1, "plan", 1_040, "provider"), (2, "plan", 1_620, "provider")]
    assert all(e["window"] == 50_000 and e["limit"] == 40_000 and e["remaining"] == 50_000 - e["used"] for e in ctx_events)
    assert ledger.data["usage"] == {"input_tokens": 2_600, "output_tokens": 60}, "the meter shows the same real usage the ledger adds up"


def test_without_a_usable_provider_count_the_event_carries_the_agents_own_estimate(repo):
    provider = Scripted([tool("read_file", path="app/calc.py"), final("it adds")])   # reports 10 in / 5 out: far below the real size
    _, ctx_events, _ = run_question(repo, provider, context_window=50_000, reserve_tokens=10_000)
    budget = Budget(50_000, 10_000)
    for event, (system, messages), reply in zip(ctx_events, provider.calls, ["read", "final"]):
        sent_reply = event["estimate"] - budget.used(system, messages)
        assert event["source"] == "estimate" and event["used"] == event["estimate"] and 0 < sent_reply < 200, reply
        assert event["reported"] == {"input_tokens": 10, "output_tokens": 5}
    assert ctx_events[1]["used"] > ctx_events[0]["used"], "the conversation grew by the tool result"
    assert ctx_events[0]["estimate"] == budget.used(*provider.calls[0]) + tokens(tool("read_file", path="app/calc.py"))


def test_the_level_climbs_as_the_conversation_fills(repo):
    files = ["app/calc.py", "app/util.py", "app/money.py", "app/old.py"]
    replies = [tool("read_file", path=p) for p in files] + [final("done")]
    provider = Usage(replies, [(8_000, 10), (20_000, 10), (33_000, 10), (38_500, 10), (39_500, 10)])
    _, ctx_events, _ = run_question(repo, provider, context_window=50_000, reserve_tokens=10_000, max_steps_per_package=10)
    assert [e["level"] for e in ctx_events] == ["ok", "ok", "warn", "critical", "critical"]
    assert ctx_events[-1]["remaining_usable"] == 40_000 - 39_510


def test_context_events_are_plain_json(repo):
    import json
    provider = Usage([final("hi")], [(700, 5)])
    _, ctx_events, _ = run_question(repo, provider)
    assert json.loads(json.dumps(ctx_events))[0]["used"] == 705
